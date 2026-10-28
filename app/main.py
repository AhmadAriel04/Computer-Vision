import time
import cv2

from app.camera.camera import Camera
from app.detector.face_detector import FaceDetector
from app.detector.emotion_classifier import EmotionClassifier
from app.tracker.face_tracker import FaceTracker
from app.selection.face_selector import FaceSelector
from app.quality.frame_quality import FrameQualityCalculator
from app.services.session_manager import SessionManager
from app.services.emotion_cache import EmotionCache
from app.services.emotion_voter import EmotionVoter
from app.services.score_aggregator import ScoreAggregator
from app.services.cv_client import CVClient
from app.engine.confidence_engine import ConfidenceEngine
from app.ui_dashboard import DashboardUI
from app.utils.config import (
    WINDOW_NAME, FACE_MODEL, EMOTION_MODEL, EMOTION_CONF,
    EMOTION_INTERVAL, MODEL_VERSION, COUNTER_ROIS,
)
from app.utils.drawing import draw, draw_counter_rois


def calculate_valence(distribution: dict) -> float:
    weights = {"happy": 1.0, "neutral": 0.0, "sad": -0.7, "angry": -1.0}
    value = sum(float(p) * weights.get(e, 0.0) for e, p in distribution.items())
    return round(max(-1.0, min(1.0, value)), 4)


def calculate_score(valence: float) -> float:
    return round(max(1.0, min(5.0, 3.8 + valence * 1.2)), 2)


def calculate_rating(score: float) -> int:
    return int(max(1, min(5, round(score))))


def build_confidence_components(summary: dict) -> dict:
    distribution = summary.get("emotion_distribution") or {}
    agreement = max(distribution.values()) if distribution else 0.0
    sample_count = summary.get("sample_count", 0)
    return {
        "adequacy": round(min(1.0, sample_count / 20.0), 4),
        "agreement": round(agreement, 4),
        "stability": round(agreement, 4),
        "model": round(float(summary.get("avg_confidence", 0.0)), 4),
        "quality": round(float(summary.get("avg_quality", 0.0)), 4),
        "decisiveness": round(agreement, 4),
    }


def process_finished_session(session_key, session_manager, aggregator,
                             confidence_engine, voter, cache, cv_client, ui):
    face_id = session_manager.get_face_id(session_key)
    counter_code = session_manager.get_counter_code(session_key)
    session_uid = session_manager.get_session_uid(session_key)
    duration = session_manager.duration(session_key)
    timestamps = session_manager.timestamps(session_key)
    frames_seen = session_manager.get_frames_seen(session_key)

    summary = aggregator.summarize(session_key)
    confidence_result = confidence_engine.evaluate(summary, duration)
    final_confidence = float(confidence_result["final_confidence"])

    print("\n" + "=" * 60)
    print(f"Session face_id   : {face_id}")
    print(f"UID               : {session_uid}")
    print(f"Counter           : {counter_code}")
    print(f"Durasi            : {duration}s")
    print(f"Frames            : {frames_seen}")
    print(f"Samples           : {summary['sample_count']}")
    print(f"Emosi dominan     : {summary['dominant_emotion']}")
    print(f"Confidence        : {final_confidence}")
    print(f"Confidence label  : {confidence_result['label']}")
    print("=" * 60)

    sent = False
    if confidence_result["reliable"] and counter_code and session_uid:
        distribution = summary["emotion_distribution"]
        valence = calculate_valence(distribution)
        score = calculate_score(valence)
        rating = calculate_rating(score)
        payload = {
            "session_uid": session_uid,
            "counter_code": counter_code,
            "started_at": timestamps["started_at"],
            "ended_at": timestamps["ended_at"],
            "duration_seconds": duration,
            "rating": rating,
            "score": score,
            "confidence": final_confidence,
            "dominant_emotion": summary["dominant_emotion"],
            "distribution": {e: distribution.get(e, 0.0) for e in ("happy", "neutral", "sad", "angry")},
            "valence": valence,
            "frames_seen": frames_seen,
            "samples_used": summary["sample_count"],
            "effective_samples": round(summary["sample_count"] * final_confidence, 3),
            "confidence_components": build_confidence_components(summary),
            "model_version": MODEL_VERSION,
        }
        print("[Main] Payload CV:")
        print(payload)
        response = cv_client.send_session(payload)
        if response:
            print("[Main] Laravel response:")
            print(response)
            sent = True
        else:
            print("[Main] Session gagal dikirim ke Laravel.")
    elif not counter_code:
        print(f"[Session {face_id}] tidak dikirim: counter_code tidak tersedia.")
    else:
        print(f"[Session {face_id}] tidak dikirim ke Laravel karena data belum reliable.")

    if counter_code:
        ui.set_latest(counter_code, summary.get("dominant_emotion", "Unknown"),
                      final_confidence, summary.get("sample_count", 0), duration,
                      "COMPLETED" if sent else "LOCAL ONLY")

    voter.clear(session_key)
    cache.clear(session_key)
    aggregator.clear(session_key)
    session_manager.remove(session_key)
    return True


def main():
    camera = Camera()
    face_detector = FaceDetector(FACE_MODEL)
    emotion_classifier = EmotionClassifier(EMOTION_MODEL)
    tracker = FaceTracker()
    selector = FaceSelector()
    quality_calculator = FrameQualityCalculator()
    session_manager = SessionManager(min_presence=2.0, max_absence=4.0)
    cache = EmotionCache()
    voter = EmotionVoter()
    aggregator = ScoreAggregator()
    confidence_engine = ConfidenceEngine()
    cv_client = CVClient()
    ui = DashboardUI(WINDOW_NAME, COUNTER_ROIS.keys())

    print("=" * 60)
    print("BSI COMPUTER VISION - INTERACTIVE MULTI COUNTER")
    print("=" * 60)
    print(f"Counters       : {', '.join(COUNTER_ROIS.keys())}")
    print(f"Model          : {MODEL_VERSION}")
    print("API            : Laravel CV API")
    print("=" * 60)

    session_total = 0
    running = True

    def process_keys(keys):
        nonlocal session_total
        processed = 0
        for key in keys:
            if key not in session_manager.sessions:
                continue
            if process_finished_session(key, session_manager, aggregator,
                                        confidence_engine, voter, cache, cv_client, ui):
                session_total += 1
                ui.set_session_count(session_total)
                processed += 1
        return processed

    def run_detection(counter_code):
        frame_count = 0
        completed = 0
        had_active_session = False
        tracker.reset()
        camera.start()
        ui.set_monitoring(True, f"Monitoring {counter_code} aktif. Kamera menyala.")
        print(f"[Camera] Kamera dimulai untuk {counter_code}.")

        try:
            while True:
                ret, frame = camera.read()
                if not ret:
                    print("[Main] Gagal membaca frame kamera.")
                    break

                frame_count += 1
                detections = face_detector.detect(frame)
                boxes = [item["box"] for item in detections]
                tracked_faces = tracker.update(boxes)

                # Hanya counter yang dipilih yang aktif untuk satu sesi pelayanan.
                selected = selector.select_by_counters(
                    tracked_faces, frame.shape,
                    {counter_code: COUNTER_ROIS[counter_code]},
                )
                draw_counter_rois(frame, {counter_code: COUNTER_ROIS[counter_code]})

                if counter_code in selected:
                    primary_face = selected[counter_code]
                    face_id = primary_face.id
                    session_key = f"{counter_code}:{face_id}"
                    active = session_manager.update_presence(session_key, face_id, counter_code)

                    if active:
                        had_active_session = True
                        session_manager.increment_frame(session_key)
                        x1, y1, x2, y2 = map(int, primary_face.box)
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                        crop = frame[y1:y2, x1:x2]
                        if crop.size and frame_count % EMOTION_INTERVAL == 0:
                            emotion, conf = emotion_classifier.predict(crop)
                            quality = quality_calculator.compute(crop)
                            if conf >= EMOTION_CONF:
                                cache.update(session_key, emotion, conf)
                                voter.add(session_key, emotion)
                            else:
                                emotion = "Unknown"
                                cache.update(session_key, emotion, conf)
                            if quality["is_good"]:
                                aggregator.add_sample(session_key, emotion, conf, quality["quality_score"])

                    result = cache.get(session_key)
                    dominant = voter.dominant(session_key)
                    display_emotion = dominant if dominant != "Unknown" else result["emotion"]
                    draw(frame, primary_face.box, display_emotion, result["confidence"], counter_code=counter_code)

                    ui.set_latest(counter_code, display_emotion, result["confidence"],
                                  aggregator.summarize(session_key)["sample_count"],
                                  session_manager.duration(session_key) if session_key in session_manager.sessions else 0,
                                  "ACTIVE" if active else "DETECTING")
                else:
                    ui.set_latest(counter_code, "Unknown", 0.0, 0, 0.0, "WAITING")

                completed += process_keys(session_manager.drain_finished())
                completed += process_keys(session_manager.cleanup())

                if ui.consume_stop():
                    print("[Main] Stop Monitoring ditekan.")
                    forced = session_manager.finish_all()
                    completed += process_keys(forced)
                    break

                key = ui.render(frame)
                if key in (27, ord("s"), ord("S")) and key == 27:
                    print("[Main] Monitoring dihentikan dengan ESC.")
                    forced = session_manager.finish_all()
                    completed += process_keys(forced)
                    break
                if key in (ord("q"), ord("Q")):
                    ui.quit_requested = True
                    forced = session_manager.finish_all()
                    completed += process_keys(forced)
                    break

                # Nasabah sudah pergi > max_absence dan session sudah dikirim.
                # Kamera otomatis mati setelah sesi pelayanan selesai.
                if had_active_session and completed > 0 and not session_manager.sessions:
                    print("[Main] Session selesai. Nasabah sudah pergi. Kamera dimatikan otomatis.")
                    break
        finally:
            camera.release()
            tracker.reset()
            ui.set_monitoring(False, f"Monitoring {counter_code} selesai. Kamera mati.")
            print("[Camera] Kamera dihentikan dan device dilepas.")
            # Bersihkan state presence yang belum aktif agar trigger berikutnya bersih.
            session_manager.presence.clear()
            session_manager.face_to_session.clear()

    while running:
        key = ui.render(None)
        if key in (ord("q"), ord("Q")):
            ui.quit_requested = True
        if key == 27:
            ui.quit_requested = True

        if ui.quit_requested:
            break

        if ui.consume_start():
            if not ui.selected_counter:
                ui.status_message = "Pilih counter terlebih dahulu."
                continue
            try:
                run_detection(ui.selected_counter)
            except RuntimeError as exc:
                ui.set_monitoring(False, f"Kamera gagal: {exc}")
                print(f"[Camera] {exc}")

    camera.release()
    cv2.destroyAllWindows()
    print("[Main] Computer Vision dihentikan.")


if __name__ == "__main__":
    main()
