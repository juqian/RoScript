from ..models.frame import Frame
import cv2

POINT_COLOR = (0,255,0)
ARROW_COLOR = (0,255,0)
WIDGET_COLOR = (0,255,0)
KEYBOARD_COLOR = (255,0,0)
KEY_COLOR = (0,0,255)
NOTE_COLOR = (0,255,0)

def get_preview(frame, objects, draw_methods):
    draw_areas = draw_methods["draw_areas"] if "draw_areas" in draw_methods else None
    draw_points = draw_methods["draw_points"] if "draw_points" in draw_methods else None
    draw_arrows = draw_methods["draw_arrows"] if "draw_arrows" in draw_methods else None
    draw_notes = draw_methods["draw_notes"] if "draw_notes" in draw_methods else None
    points = objects["points"] if "points" in objects else None
    areas = objects["areas"] if "areas" in objects else None
    notes = objects["notes"] if "notes" in objects else None
    preview_image = frame.overlook_image.copy()
    if areas:
        draw_areas(preview_image, areas)
    if points:
        draw_points(preview_image, points)
        if draw_arrows:
            draw_arrows(preview_image, points)
    device_preview_image = Frame(None, frame.parent, preview_image, None).get_device_image()
    if notes:
        draw_notes(device_preview_image, notes)
    return device_preview_image

class DrawPointMethods:
    @staticmethod
    def dot(image, points):
        for point in points:
            cv2.circle(image,point,3,POINT_COLOR,6)

    @staticmethod
    def tilted_cross(image, points):
        for point in points:
            cv2.drawMarker(image,point,POINT_COLOR,cv2.MARKER_TILTED_CROSS,12,2)

    @staticmethod
    def concentric_circles(image, points):
        for point in points:
            cv2.circle(image,point,2,POINT_COLOR,4)
            cv2.circle(image,point,8,POINT_COLOR,2)

class DrawArrowMethods:
    @staticmethod
    def default(image, points):
        for i in range(1, len(points)):
            start_point, end_point = points[i-1], points[i]
            cv2.arrowedLine(image, start_point, end_point, ARROW_COLOR,2,8,0,0.1)

class DrawAreaMethods:
    @staticmethod
    def widget(image, areas):
        for area in areas:
            cv2.rectangle(image,area.lt,area.rb,WIDGET_COLOR,2)

    @staticmethod
    def keyboard(image, areas):
        keyboard_area = areas[0]
        key_areas = areas[1:]
        for area in key_areas:
            cv2.rectangle(image,area.lt,area.rb,KEY_COLOR,2)
        cv2.rectangle(image,keyboard_area.lt,keyboard_area.rb,KEYBOARD_COLOR,2)

class DrawNoteMethods:
    @staticmethod
    def default(image, notes):
        current_draw_position_x = 40
        current_draw_position_y = 40
        line_gap = 50
        for note in notes:
            cv2.putText(image, note, (current_draw_position_x,current_draw_position_y), cv2.FONT_HERSHEY_COMPLEX, 1.1, NOTE_COLOR, 3)
            current_draw_position_y += line_gap


