import os
import json
from PIL import Image
import numpy as np
from scipy.ndimage import label, binary_dilation

os.makedirs('website/assets/components', exist_ok=True)

img = Image.open('website/assets/breakdown-jericho-glasses.jpg')
arr = np.array(img)
top_arr = arr[:520, :, :3]
is_fg = np.any(top_arr < 240, axis=2)
labeled, num_features = label(is_fg)

def extract_mask_rgba(image_rgb, mask, threshold=245.0, feather=18.0, dilation=2, min_opacity=0.0):
    mask_dil = binary_dilation(mask, iterations=dilation) if dilation > 0 else mask
    min_ch = np.min(image_rgb, axis=2).astype(np.float32)
    alpha = np.zeros(mask.shape, dtype=np.float32)
    alpha[mask_dil] = np.clip((threshold - min_ch[mask_dil]) / feather, 0.0, 1.0) * 255.0
    if min_opacity > 0:
        alpha[mask] = np.maximum(alpha[mask], min_opacity)
        
    rgb = image_rgb.astype(np.float32)
    a_norm = np.clip(alpha / 255.0, 0.001, 1.0)[:, :, np.newaxis]
    rgb = (rgb - 248.0 * (1.0 - a_norm)) / a_norm
    rgb = np.clip(rgb, 0.0, 255.0)
    
    res = np.dstack([rgb.astype(np.uint8), alpha.astype(np.uint8)])
    return Image.fromarray(res, 'RGBA')

# 1. Temple arm (label_val 2)
temple_mask = (labeled == 2)
temple_img = extract_mask_rgba(top_arr, temple_mask, min_opacity=200.0)
temple_bbox = temple_img.getbbox()
temple_cropped = temple_img.crop(temple_bbox)
temple_cropped.save('website/assets/components/part-temple.png')

# 2. Speaker (label_val 40)
speaker_mask = (labeled == 40)
speaker_img = extract_mask_rgba(top_arr, speaker_mask, min_opacity=180.0)
speaker_bbox = speaker_img.getbbox()
speaker_cropped = speaker_img.crop(speaker_bbox)
speaker_cropped.save('website/assets/components/part-speaker.png')

# 3. Battery (label_val 41)
battery_mask = (labeled == 41)
battery_img = extract_mask_rgba(top_arr, battery_mask, min_opacity=180.0)
battery_bbox = battery_img.getbbox()
battery_cropped = battery_img.crop(battery_bbox)
battery_cropped.save('website/assets/components/part-battery.png')

# 4. NPU Chip (label_val 38)
npu_mask = (labeled == 38)
npu_img = extract_mask_rgba(top_arr, npu_mask, min_opacity=180.0)
npu_bbox = npu_img.getbbox()
npu_cropped = npu_img.crop(npu_bbox)
npu_cropped.save('website/assets/components/part-npu.png')

# 5. Flex Ribbon Cable (label_val 39)
cable_mask = (labeled == 39)
cable_img = extract_mask_rgba(top_arr, cable_mask, min_opacity=180.0)
cable_bbox = cable_img.getbbox()
cable_cropped = cable_img.crop(cable_bbox)
cable_cropped.save('website/assets/components/part-cable.png')

# 6. Front Frame & Lenses (label_val 1, plus label_val 3 which is the small sensor dot at 820..854)
frame_mask = (labeled == 1) | (labeled == 3)
frame_img = extract_mask_rgba(top_arr, frame_mask, threshold=244.0, feather=16.0, dilation=1)
frame_bbox = frame_img.getbbox()
frame_cropped = frame_img.crop(frame_bbox)
frame_cropped.save('website/assets/components/part-frame.png')

# 7. Front Camera Module (extracted from the right lens socket)
# The camera module inside the lens is located at x=[620:860], y=[140:240]
cam_crop = top_arr[140:240, 620:860]
cam_mask = np.any(cam_crop < 225, axis=2)
# Dilate and extract
cam_img = extract_mask_rgba(cam_crop, cam_mask, threshold=235.0, feather=14.0, dilation=1, min_opacity=160.0)
cam_bbox = cam_img.getbbox()
cam_cropped = cam_img.crop(cam_bbox)
cam_cropped.save('website/assets/components/part-camera.png')
# Adjust bbox to canvas coordinates
actual_cam_bbox = (620 + cam_bbox[0], 140 + cam_bbox[1], 620 + cam_bbox[2], 140 + cam_bbox[3])

# 8. Subtle contact shadow
shadow_mask = (labeled == 70) | (labeled == 73) | (labeled == 91)
shadow_img = extract_mask_rgba(top_arr, shadow_mask, threshold=247.0, feather=10.0, dilation=1)
shadow_bbox = shadow_img.getbbox()
if shadow_bbox:
    shadow_cropped = shadow_img.crop(shadow_bbox)
    shadow_cropped.save('website/assets/components/part-shadow.png')

# 9. Assembled Side Profile (bottom half of image)
bottom_arr = arr[510:980, :, :3]
bottom_fg = np.any(bottom_arr < 240, axis=2)
bottom_labeled, _ = label(bottom_fg)
# Main side profile is the largest component
profile_mask = (bottom_labeled == 1)
profile_img = extract_mask_rgba(bottom_arr, profile_mask, threshold=246.0, feather=18.0, dilation=2, min_opacity=200.0)
profile_bbox = profile_img.getbbox()
profile_cropped = profile_img.crop(profile_bbox)
profile_cropped.save('website/assets/components/jericho-profile-assembled.png')

# Save coordinate metadata relative to canvas 1800x520
metadata = {
    "canvas": {"width": 1800, "height": 520},
    "parts": {
        "frame": {
            "file": "website/assets/components/part-frame.png",
            "bbox": frame_bbox,
            "x": frame_bbox[0], "y": frame_bbox[1],
            "w": frame_bbox[2] - frame_bbox[0], "h": frame_bbox[3] - frame_bbox[1]
        },
        "temple": {
            "file": "website/assets/components/part-temple.png",
            "bbox": temple_bbox,
            "x": temple_bbox[0], "y": temple_bbox[1],
            "w": temple_bbox[2] - temple_bbox[0], "h": temple_bbox[3] - temple_bbox[1]
        },
        "camera": {
            "file": "website/assets/components/part-camera.png",
            "bbox": list(actual_cam_bbox),
            "x": actual_cam_bbox[0], "y": actual_cam_bbox[1],
            "w": actual_cam_bbox[2] - actual_cam_bbox[0], "h": actual_cam_bbox[3] - actual_cam_bbox[1]
        },
        "speaker": {
            "file": "website/assets/components/part-speaker.png",
            "bbox": speaker_bbox,
            "x": speaker_bbox[0], "y": speaker_bbox[1],
            "w": speaker_bbox[2] - speaker_bbox[0], "h": speaker_bbox[3] - speaker_bbox[1]
        },
        "battery": {
            "file": "website/assets/components/part-battery.png",
            "bbox": battery_bbox,
            "x": battery_bbox[0], "y": battery_bbox[1],
            "w": battery_bbox[2] - battery_bbox[0], "h": battery_bbox[3] - battery_bbox[1]
        },
        "npu": {
            "file": "website/assets/components/part-npu.png",
            "bbox": npu_bbox,
            "x": npu_bbox[0], "y": npu_bbox[1],
            "w": npu_bbox[2] - npu_bbox[0], "h": npu_bbox[3] - npu_bbox[1]
        },
        "cable": {
            "file": "website/assets/components/part-cable.png",
            "bbox": cable_bbox,
            "x": cable_bbox[0], "y": cable_bbox[1],
            "w": cable_bbox[2] - cable_bbox[0], "h": cable_bbox[3] - cable_bbox[1]
        },
        "profile": {
            "file": "website/assets/components/jericho-profile-assembled.png",
            "bbox": profile_bbox,
            "w": profile_bbox[2] - profile_bbox[0], "h": profile_bbox[3] - profile_bbox[1]
        }
    }
}

with open('website/assets/components/components.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print('Extraction complete!')
for name, d in metadata['parts'].items():
    print(f"{name}: {d.get('w')}x{d.get('h')} at ({d.get('x', '-')}, {d.get('y', '-')})")
