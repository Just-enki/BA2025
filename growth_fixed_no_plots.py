import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import sys

sys.path.insert(1, './python')

import cam1_ROIs
import cam2_ROIs
import cam1_1_ROIs
import cam2_2_ROIs

def parse_datetime_from_filename(filename):
    try:
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split('_')
        if len(parts) >= 4:
            if parts[-1].lower() == 'ndvi':
                parts = parts[:-1]
            if len(parts) >= 4:
                day, month, hour, minute = [int(p) for p in parts[:4]]
                return datetime(datetime.now().year, month, day, hour, minute)
    except (ValueError, IndexError):
        pass
    return datetime(1900, 1, 1)

def get_rois_for_image(filepath):

    filepath = str(filepath)
    parts = filepath.split(os.sep)
    ba_folder, date_folder, cam_num, roi_module = None, None, None, None

    path_map = {
        'ba_1_organized': (1, cam1_ROIs),
        'ba_2_organized': (2, cam2_ROIs),
        'ba_1_1_organized': (3, cam1_1_ROIs),
        'ba_2_2_organized': (4, cam2_2_ROIs),
    }
    date_folders_list = ['Aug_26', 'Aug_27','Aug_28','Aug_29','Aug_30','Aug_31', 'Sep_01', 'Sep_02', 'Sep_03', 'Sep_04', 'Sep_05',
                         'Sep_06', 'Sep_07', 'Sep_08', 'Sep_09', 'Sep_10', 'Sep_11', 'Sep_12', 'Sep_13', 'Sep_14', 'Sep_15']

    for part in parts:
        for folder_name, (cam, module) in path_map.items():
            if folder_name in part:
                ba_folder, cam_num, roi_module = folder_name, cam, module
        if part in date_folders_list:
            date_folder = part

    if not ba_folder or not date_folder:
        raise ValueError(f" invalid: {filepath}")

    roi_variable_name = date_folder.replace('Sep_', 'Sept_')

    try:
        roi_set = getattr(roi_module, roi_variable_name)
        return roi_set['plant_roi'], roi_set['white_roi'], roi_set['dark_roi'], cam_num
    except AttributeError:
        raise AttributeError(f"Could not find ROI '{roi_variable_name}' in the ROI file for cam {cam_num}.")

def compute_ndvi(image_path, rois, save_prefix="ndvi_output", output_dir=None, generate_plots=False):

    img = Image.open(image_path).convert("RGB")
    arr = np.asarray(img).astype(np.float32)

    def roi_slice(a, roi):
        x1, y1, x2, y2 = roi
        return a[y1:y2, x1:x2]

    # Normalization 
    dark_roi = roi_slice(arr, rois['dark_roi'])
    white_roi = roi_slice(arr, rois['white_roi'])
    dark_mean = dark_roi.reshape(-1, 3).mean(axis=0)
    white_mean = white_roi.reshape(-1, 3).mean(axis=0)
    den = (white_mean - dark_mean)
    den[den == 0] = 1.0
    norm = (arr - dark_mean) / den
    norm = np.clip(norm, 0, 1)

    nir = norm[..., 0]  # Red channel for NIR
    vis = norm[..., 2]  #Blue channel for Visible
    eps = 1e-6
    ndvi = (nir - vis) / (nir + vis + eps)
    ndvi = np.clip(ndvi, -1, 1)

    # Plant ROI
    plant = roi_slice(ndvi, rois['plant_roi']).flatten()
    plant = plant[~np.isnan(plant)]
    
    # Growth Metric
    green_pixel_count = float(np.sum(plant > 0.1))

    stats = {
        "mean": float(np.mean(plant)),
        "median": float(np.median(plant)),
        "std": float(np.std(plant)),
        "min": float(np.min(plant)),
        "max": float(np.max(plant)),
        "growth_metric": green_pixel_count,
    }


    if generate_plots:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            save_prefix = os.path.join(output_dir, Path(image_path).stem)

       
        plt.figure(figsize=(6,4)); plt.imshow(ndvi, vmin=-1, vmax=1, cmap="RdYlGn"); plt.title("NDVI (full frame)"); plt.axis('off'); plt.colorbar(label="NDVI"); plt.savefig(f"{save_prefix}_full.png", bbox_inches='tight', pad_inches=0.05); plt.close()
        plt.figure(figsize=(6,4)); x1, y1, x2, y2 = rois['plant_roi']; plt.imshow(ndvi[y1:y2, x1:x2], vmin=-1, vmax=1, cmap="RdYlGn"); plt.title("NDVI (plant ROI)"); plt.axis('off'); plt.colorbar(label="NDVI"); plt.savefig(f"{save_prefix}_plant.png", bbox_inches='tight', pad_inches=0.05); plt.close()
        plt.figure(figsize=(6,4)); plt.hist(plant, bins=50, range=(-1, 1), color="green", alpha=0.7); plt.title("NDVI Histogram (plant ROI)"); plt.xlabel("NDVI value"); plt.ylabel("Pixel count"); plt.grid(True, alpha=0.3); plt.savefig(f"{save_prefix}_hist.png", bbox_inches='tight', pad_inches=0.05); plt.close()

    return stats

def batch_process_all_directories(base_directory="."):
    """
    Process all subdirectories in ba_1_organized and ba_2_organized
    """
    base_dir = Path(base_directory)
    all_results = []
    
    for cam_dir in [base_dir / "ba_1_organized", base_dir / "ba_2_organized", base_dir / "ba_1_1_organized",base_dir / "ba_2_2_organized"]:
        if not cam_dir.exists():
            print(f"Warning: Directory {cam_dir} does not exist")
            continue
            
        for date_dir in cam_dir.iterdir():
            if date_dir.is_dir() and date_dir.name in ['Aug_26','Aug_27','Aug_28','Aug_29','Aug_30','Aug_31', 'Sep_01', 'Sep_02', 'Sep_03', 'Sep_04', 'Sep_05', 'Sep_06', 'Sep_07', 'Sep_08', 'Sep_09', 'Sep_10', 'Sep_11', 'Sep_12', 'Sep_13', 'Sep_14', 'Sep_15']:
                print(f"Processing {date_dir}")
                
                try:
                    sample_image = next(date_dir.glob("*.jpg"), None)
                    if sample_image:
                        plant_roi, white_roi, dark_roi, cam_num = get_rois_for_image(sample_image)
                        rois = {'plant_roi': plant_roi, 'white_roi': white_roi, 'dark_roi': dark_roi}
                        
                        for img_path in sorted(date_dir.glob("*.jpg")):
                            try:
                                output_dir = date_dir / "data"
                                stats = compute_ndvi(img_path, rois, output_dir=output_dir)
                                stats["image"] = img_path.name
                                stats["camera"] = f"ba_{cam_num}"
                                stats["date_folder"] = date_dir.name
                                stats["datetime"] = parse_datetime_from_filename(img_path.name)
                                all_results.append(stats)
                                print(f"Processed {img_path.name}")
                            except Exception as e:
                                print(f"Error processing {img_path}: {e}")
                    else:
                        print(f"No images found in {date_dir}")
                except Exception as e:
                    print(f"Error getting ROIs for {date_dir}: {e}")
    
    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values("datetime")
        output_csv = base_dir / "ndvi_all_results_growth.csv"
        df.to_csv(output_csv, index=False)
        print(f"Saved results to {output_csv}")
        return df
    else:
        print("No results to save")
        return pd.DataFrame()

if __name__ == "__main__":
    df = batch_process_all_directories()
    print(df.head())