import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.messagebox import showinfo
import cv2
from PIL import Image, ImageTk
from random import randint, uniform
import numpy as np
from scipy.interpolate import splprep, splev
from ultralytics import YOLO

def draw_smooth_cobble_curve(image, target_center, scale_factor=0.4, random_color=None):
    num_points = 7

    x = [0, 0 + np.random.randint(0, 20)]
    y = [250, 250 + np.random.randint(10, 15)]
    x_var = np.random.randint(0, 200, num_points - 2)
    y_var = np.random.randint(50, 250, num_points - 2)   
    x += x_var.tolist()
    y += y_var.tolist()

    # Generar los puntos para la curva
    tck, u = splprep([x, y], s=2000, k=5)
    unew = np.linspace(0, 1, 2000)
    out = splev(unew, tck)
    curve_points = np.array(list(zip(out[0], out[1])), np.int32).reshape((-1, 1, 2))

    # Calcular el centro para posicionarlo
    center_x, center_y = np.mean(curve_points[:, 0, :], axis=0)
    shift_x = target_center[0] - center_x
    shift_y = target_center[1] - center_y
    curve_points = curve_points + np.array([shift_x, shift_y], dtype=np.int32)

    # Escalar la curva
    curve_points = ((curve_points - target_center) * scale_factor + target_center).astype(np.int32)

    # Imagen en blanco para contener las curvas
    cobble_overlay = np.zeros_like(image)

    # varias curvas para simular el brillo
    for _ in range(4,6):
        random_thickness = randint(25, 35)
        random_alpha = uniform(0.5, 1)
        temp_overlay = cobble_overlay.copy()
        cv2.polylines(temp_overlay, [curve_points], isClosed=False, color=random_color, thickness=int(random_thickness * scale_factor))
        cv2.addWeighted(temp_overlay, random_alpha, cobble_overlay, 1 - random_alpha, 0, cobble_overlay)

    # Blur 
    cobble_overlay = cv2.GaussianBlur(cobble_overlay, (25, 25), 10)

    # Curva blanca
    temp_overlay = cobble_overlay.copy()
    random_alpha_white = uniform(0.8, 1)
    random_thickness_white = randint(10,13)
    cv2.polylines(temp_overlay, [curve_points], isClosed=False, color=(255, 255, 255), thickness=int(random_thickness_white * scale_factor))
    cv2.addWeighted(temp_overlay, random_alpha_white, cobble_overlay, 1 - random_alpha_white, 0, cobble_overlay)

    # Finally, blend the overlay with the original image
    cv2.addWeighted(cobble_overlay, 1, image, 1, 0, image)

def generate_cobbles(image, centers, scale_factor=0.4):
    random_color = (randint(10, 20), randint(10, 20), randint(200, 255)) 
    centers = [x for item in centers for x in (item, item)]
    for center in centers:
        draw_smooth_cobble_curve(image, target_center=center, scale_factor=scale_factor, random_color=random_color)
    return image

def annotate_with_model(model,frame,conf_threshold):
    results = model.predict(frame, conf=conf_threshold, save=False, augment = True, iou = 0.9)                    
    if results[0].boxes:
        annotated_frame = results[0].plot()
    else:
        annotated_frame = frame
    return annotated_frame

class CobbleDetectionApp:  
    def __init__(self, root):
        self.root = root
        self.root.title("Cobble Detection App v1.0")

        # Initialize video variables
        self.video_path = None
        self.cap = None
        self.conf_threshold = 0.5
        self.is_generating = False
        self.is_processing = False
        self.centers = []
        
        self.image_to_save = None

        self.model = YOLO("best16.pt")

        # Create UI elements
        self.create_ui()

    def create_ui(self):
        # Main menu
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Open Video", command=self.load_video)
        file_menu.add_command(label="Save Frame", command=self.save_frame)  # New Save Frame option
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="About", command=lambda: showinfo(
            "About", 
            "Cobble Detection App v1.0\n"
            "Hecho por Eybert Macedo\n"
            "Esta aplicación tiene las siguientes características:\n"
            "- Detección de curvas de cobble en videos utilizando YOLO.\n"
            "- Generación de curvas suaves para simular la caída de cobbles.\n"
            "- Ajuste de umbral de confianza para la detección en tiempo real.\n"
            "- Interfaz gráfica fácil de usar con control deslizante para ajustar el umbral.\n"
            "- Carga y procesamiento de videos con visualización en vivo.\n"
            "- Detección de cobbles generadas en puntos seleccionados por el usuario en el video.\n"
            "- Posibilidad de activar/desactivar la generación de curvas y el procesamiento del video en tiempo real."
        ))

        menu.add_cascade(label="Help", menu=help_menu)

        # Video display panel
        self.video_panel = tk.Label(self.root, text="La grabación se mostrará aqui", bg="gray")
        self.video_panel.pack(pady=10, fill=tk.BOTH, expand=True)

        # Controls
        controls_frame = tk.Frame(self.root)
        controls_frame.pack()

        self.conf_threshold_label = tk.Label(controls_frame, text=f"Threshold: {self.conf_threshold:.2f}")
        self.conf_threshold_label.grid(row=0, column=0, padx=5)

        self.conf_threshold_slider = ttk.Scale(
            controls_frame, from_=0.1, to=1.0, value=self.conf_threshold, orient="horizontal", command=self.update_threshold
        )
        self.conf_threshold_slider.grid(row=0, column=1, padx=5)

        self.generate_button = tk.Button(controls_frame, text="Start Generation", command=self.toggle_generation)
        self.generate_button.grid(row=0, column=2, padx=5)

        self.process_button = tk.Button(controls_frame, text="Process Video", command=self.toggle_process_video)
        self.process_button.grid(row=0, column=3, padx=5)

        # Bind mouse click event
        self.video_panel.bind("<Button-1>", self.on_mouse_click)

    def load_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*")])
        if file_path:
            self.video_path = file_path
            self.cap = cv2.VideoCapture(file_path)
            self.display_frame()

    def save_frame(self):
        if not self.cap:
            showinfo("Error", "No video loaded.")
            return

         # Resize and convert frame to an image that can be saved
        frame = self.image_to_save 
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        # Open the save file dialog
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            pil_image.save(file_path)
            showinfo("Success", f"Frame saved as {file_path}")

    def update_threshold(self, value):
        self.conf_threshold = float(value)
        self.conf_threshold_label.config(text=f"Threshold: {self.conf_threshold:.2f}")

    def toggle_generation(self):
        if not self.cap:
            showinfo("Error", "No video loaded.")
            return
        else:
            self.is_generating = not self.is_generating
            self.generate_button.config(text="Stop Generation" if self.is_generating else "Start Generation")

    def toggle_process_video(self):
        if not self.cap:
            showinfo("Error", "No video loaded.")
            return
        else: 
            self.is_processing = not self.is_processing
            self.process_button.config(text="Stop Processing" if self.is_processing else "Process Video")

    def process_video(self): 
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
        
            # Display frame
            frame = self.resize_frame(frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
            self.video_panel.config(image=img)
            self.video_panel.image = img

            self.root.update_idletasks()
            self.root.update()

        self.cap.release()

    def display_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()

        if self.is_generating:
            frame = generate_cobbles(frame, self.centers, scale_factor=0.4)

        if self.is_processing:
            overlay = f"Threshold: {self.conf_threshold:.2f}"
            cv2.putText(frame, overlay, (30, 60), cv2.FONT_HERSHEY_DUPLEX, 2, (255,0,0), 3)
            frame = annotate_with_model(self.model, frame, self.conf_threshold)
        
        self.image_to_save = frame

        if ret:
            frame = self.resize_frame(frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
            self.video_panel.config(image=img)
            self.video_panel.image = img
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video

        self.root.after(30, self.display_frame)

    def resize_frame(self, frame):
        desired_width = 800
        desired_height = 550
        self.scale_x = desired_width / frame.shape[1]
        self.scale_y = desired_height / frame.shape[0]
        return cv2.resize(frame, (desired_width, desired_height))

    def on_mouse_click(self, event):
        # Adjust mouse click coordinates based on the scaling factor
        x = int(event.x / self.scale_x)
        y = int(event.y / self.scale_y)- 100

        # Save the adjusted coordinates
        self.centers.append((x, y))

if __name__ == "__main__":
    root = tk.Tk()
    app = CobbleDetectionApp(root)
    root.geometry("800x750")
    root.mainloop()