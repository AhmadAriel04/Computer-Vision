import math

def centroid(box):

    x1,y1,x2,y2 = box

    return (
        (x1+x2)//2,
        (y1+y2)//2
    )


def distance(box1, box2):

    c1 = centroid(box1)

    c2 = centroid(box2)

    return math.sqrt(
        (c1[0]-c2[0])**2 +
        (c1[1]-c2[1])**2
    )