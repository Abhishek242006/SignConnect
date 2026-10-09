"""Supported sign vocabulary.

The gestures below are PROJECT-DEFINED static hand shapes (one hand, one frame),
not official ASL/ISL signs. Many real signs involve motion, which a single-frame
landmark model cannot capture. Add a new sign by appending one entry here, then
collect data and re-train (see README).
"""

SIGNS = [
    {"word": "Hello", "gesture": "Open hand, fingers spread wide, palm to camera.", "meaning": "A greeting."},
    {"word": "Thank You", "gesture": "Flat hand tilted to the side, fingers together, thumb out.", "meaning": "Expressing gratitude."},
    {"word": "Yes", "gesture": "Closed fist, thumb resting across the fingers.", "meaning": "Agreement."},
    {"word": "No", "gesture": "Index and middle finger straight and together, thumb touching them.", "meaning": "Disagreement."},
    {"word": "Help", "gesture": "Fist with the thumb pointing straight up.", "meaning": "Asking for assistance.", "emergency": True},
    {"word": "Please", "gesture": "Flat hand, fingers together, thumb tucked, palm to camera.", "meaning": "A polite request."},
    {"word": "Stop", "gesture": "Flat hand held sideways like a blade, fingers together.", "meaning": "Stop what you are doing."},
    {"word": "Good", "gesture": "'OK' shape: thumb and index fingertip touch, other fingers extended.", "meaning": "Something is positive."},
    {"word": "Bad", "gesture": "Fist with the thumb pointing down.", "meaning": "Something is negative."},
    {"word": "Water", "gesture": "'W' shape: index, middle and ring fingers up and spread.", "meaning": "I need water."},
    {"word": "Food", "gesture": "All fingertips pinched together, pointing at the camera.", "meaning": "I need food."},
    {"word": "Emergency", "gesture": "Index and little finger up, other fingers folded ('horns').", "meaning": "Urgent danger.", "emergency": True},
    {"word": "Doctor", "gesture": "Thumb, index and middle finger extended; ring and little folded.", "meaning": "I need a doctor."},
    {"word": "Call", "gesture": "'Phone' shape: thumb and little finger extended, others folded.", "meaning": "Call someone."},
    {"word": "Sorry", "gesture": "Fist with only the little finger extended.", "meaning": "An apology."},
    {"word": "I", "gesture": "Only the index finger extended, pointing up.", "meaning": "Referring to myself."},
    {"word": "You", "gesture": "Only the index finger extended, pointing sideways.", "meaning": "Referring to the other person."},
]

for _s in SIGNS:
    _s["slug"] = _s["word"].lower().replace(" ", "-")

WORDS = [s["word"] for s in SIGNS]
EMERGENCY_WORDS = {s["word"] for s in SIGNS if s.get("emergency")}
