import cv2
import numpy as np

def _get_skew_angle(image: np.ndarray) -> float:
    """Find the skew angle of an image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Use Hough transform to find lines
    lines = cv2.HoughLinesP(thresh, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    
    if lines is None:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.rad2deg(np.arctan2(y2 - y1, x2 - x1))
        angles.append(angle)

    # Filter out horizontal/vertical lines and get the median angle
    angles = [angle for angle in angles if abs(angle) < 45]
    if not angles:
        return 0.0
        
    median_angle = np.median(angles)
    return median_angle

def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate an image to correct for skew."""
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Loads an image, de-skews it, and applies sharpening.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not found or unable to read")
        
    angle = _get_skew_angle(image)
    if abs(angle) > 0.05: # Only rotate if skew is significant
        image = _rotate_image(image, angle)
    
    # Sharpen the image using an unsharp masking technique
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)
    
    return sharpened 