import matplotlib.pyplot as plt
import numpy as np

def plot_radar_image(ax, image, title, cmap='viridis'):
    im = ax.imshow(image, aspect='auto', cmap=cmap, 
                   extent=[0, 360, 300, 0])
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, label="Intensity")
    return im

def plot_fusion_rgb(ax, fusion):
    ax.imshow(fusion, aspect='auto', extent=[0, 360, 300, 0])
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel("Range (km)")
    ax.set_title("Blue-Halo IR Fusion Visualization")
