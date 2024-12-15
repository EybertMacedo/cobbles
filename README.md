<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demo Interactiva: Ajuste de Detecciones</title>
    <style>
        body {
            background-color: #1e293b; /* Fondo oscuro moderno */
            color: #e2e8f0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            flex-col: column;
            align-items: center;
            justify-content: flex-start;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        h2 {
            margin-bottom: 10px;
        }

        p.instructions {
            background-color: #334155;
            padding: 10px 20px;
            border-radius: 8px;
            border-left: 4px solid #f97316; /* Naranja industrial */
            margin-bottom: 20px;
            font-size: 0.9rem;
        }

        .canvas-container {
            box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
            border-radius: 4px;
            overflow: hidden;
            border: 2px solid #475569;
        }

        canvas {
            display: block; /* Elimina espacio extra debajo del canvas */
            cursor: crosshair; /* Cursor para indicar precisión */
        }
        
        /* Cuando se está arrastrando algo */
        canvas.dragging {
            cursor: grabbing;
        }
    </style>
</head>
<body>

    <h2>Visor de Detección Industrial v2.1</h2>
    <p class="instructions">
        <strong>Modo Interactivo:</strong> Haz clic izquierdo y arrastra sobre los cuadros naranjas para ajustar su posición manualmente. Asegúrate de que "original.jpg" esté en la misma carpeta.
    </p>

    <div class="canvas-container">
        <canvas id="mainCanvas" width="800" height="600"></canvas>
    </div>


    <script>
        // --- Configuración Inicial ---
        const canvas = document.getElementById('mainCanvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        // IMPORTANTE: La imagen debe estar en la misma carpeta y llamarse así
        img.src = 'original.jpg'; 

        // Colores estilo "Industrial Moderno"
        const THEME_COLOR = '249, 115, 22'; // Naranja RGB
        const BOX_BORDER_COLOR = `rgb(${THEME_COLOR})`;
        const BOX_FILL_COLOR = `rgba(${THEME_COLOR}, 0.15)`; // Transparente
        const LABEL_BG_COLOR = `rgba(${THEME_COLOR}, 0.85)`; // Semi-opaco
        const LABEL_TEXT_COLOR = '#1a1a1a'; // Casi negro

        // --- Estructura de Datos ---
        // Aquí definimos las cajas iniciales. En una app real, esto vendría del backend.
        // Usamos x, y (esquina superior izquierda), w (ancho), h (alto).
        let boxes = [
            { x: 50,  y: 400, w: 80,  h: 120, label: 'steel_cobble', score: 0.60, isDragging: false },
            { x: 550, y: 380, w: 70,  h: 90,  label: 'steel_cobble', score: 0.91, isDragging: false },
            { x: 600, y: 580, w: 90,  h: 80,  label: 'steel_cobble', score: 0.66, isDragging: false }
        ];

        let dragStartX, dragStartY;

        // --- Función Principal de Dibujo ---
        function draw() {
            // 1. Limpiar el canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 2. Dibujar la imagen de fondo (si está cargada)
            if (img.complete) {
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            } else {
                 // Mensaje de error si no carga la imagen
                ctx.font = "20px Arial";
                ctx.fillStyle = "red";
                ctx.fillText("Error: No se encuentra 'original.jpg'", 50, 50);
                return;
            }

            // 3. Dibujar cada caja
            boxes.forEach(box => {
                drawModernBox(box);
            });
        }

        // Función auxiliar para dibujar una sola caja con estilo moderno
        function drawModernBox(box) {
            const paddingX = 8;
            const paddingY = 4;
            const labelText = `${box.label.toUpperCase()} ${box.score.toFixed(2)}`;
            ctx.font = 'bold 12px sans-serif';
            const textMetrics = ctx.measureText(labelText);
            const textHeight = 12; // Aproximación para la fuente
            const labelWidth = textMetrics.width + (paddingX * 2);
            const labelHeight = textHeight + (paddingY * 2);

            // A. Relleno semitransparente de la caja (efecto "high-tech")
            ctx.fillStyle = BOX_FILL_COLOR;
            ctx.fillRect(box.x, box.y, box.w, box.h);

            // B. Borde de la caja
            ctx.strokeStyle = BOX_BORDER_COLOR;
            ctx.lineWidth = 2;
            ctx.strokeRect(box.x, box.y, box.w, box.h);

            // C. Fondo de la etiqueta (arriba de la caja)
            let labelY = box.y - labelHeight;
            // Si la etiqueta se sale por arriba, ponerla dentro de la caja
            if (labelY < 0) labelY = box.y;
            
            ctx.fillStyle = LABEL_BG_COLOR;
            ctx.fillRect(box.x, labelY, labelWidth, labelHeight);

            // D. Texto de la etiqueta
            ctx.fillStyle = LABEL_TEXT_COLOR;
            ctx.textBaseline = 'top';
            ctx.fillText(labelText, box.x + paddingX, labelY + paddingY);
        }


        // --- Manejo de Eventos del Ratón (La lógica de arrastrar) ---

        // Helper: Obtener coordenadas del ratón relativas al canvas
        function getMousePos(evt) {
            var rect = canvas.getBoundingClientRect();
            return {
                x: evt.clientX - rect.left,
                y: evt.clientY - rect.top
            };
        }

        // Helper: Detectar si un punto está dentro de un rectángulo
        function isPointInRect(px, py, rect) {
            return (px >= rect.x && px <= rect.x + rect.w && py >= rect.y && py <= rect.y + rect.h);
        }


        canvas.addEventListener('mousedown', function(e) {
            const mousePos = getMousePos(e);
            // Iteramos al revés (del último al primero) para que si hay cajas superpuestas,
            // se seleccione la que se dibujó encima.
            for (let i = boxes.length - 1; i >= 0; i--) {
                if (isPointInRect(mousePos.x, mousePos.y, boxes[i])) {
                    boxes[i].isDragging = true;
                    // Guardamos el offset para que el arrastre sea suave y no salte al centro
                    dragStartX = mousePos.x - boxes[i].x;
                    dragStartY = mousePos.y - boxes[i].y;
                    canvas.classList.add('dragging'); // Cambiar cursor
                    return; // Solo arrastramos una a la vez
                }
            }
        });

        canvas.addEventListener('mousemove', function(e) {
            const mousePos = getMousePos(e);
            let isAnyDragging = false;
            
            for (let i = 0; i < boxes.length; i++) {
                if (boxes[i].isDragging) {
                    // Actualizar posición
                    boxes[i].x = mousePos.x - dragStartX;
                    boxes[i].y = mousePos.y - dragStartY;
                    isAnyDragging = true;
                }
            }

            if (isAnyDragging) {
                draw(); // Redibujar si algo se movió
            }
        });

        // Soltar el clic en cualquier parte del documento
        document.addEventListener('mouseup', function(e) {
            canvas.classList.remove('dragging');
            boxes.forEach(box => box.isDragging = false);
        });


        // --- Inicialización ---
        img.onload = function() {
             // Ajustar el tamaño del canvas al de la imagen real
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;
            // Escalar visualmente el canvas si es muy grande para la pantalla (opcional CSS)
            if(canvas.width > window.innerWidth * 0.9) {
               canvas.style.width = '90%';
               canvas.style.height = 'auto';
            }
            draw();
        };

        // Intentar dibujar al principio (por si la imagen falla, mostrar el error)
        setTimeout(draw, 100);

    </script>
</body>
</html>