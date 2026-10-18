# 📊 DataTab

Pruebaaaa

**Plataforma web de análisis estadístico para investigación médica y académica.**

DataTab transforma archivos Excel y CSV en resultados estadísticos claros: tablas de frecuencia, gráficos interactivos y cruces de variables, sin necesidad de conocimientos avanzados de programación.

---

## ✨ Funcionalidades

- 📁 **Carga de archivos** — Soporte para `.xlsx`, `.xls` y `.csv` (hasta 5MB)
- 📊 **Tablas de frecuencia** — Frecuencias absolutas y porcentajes automáticos
- 🔢 **Rangos personalizados** — Agrupación numérica: `<30`, `30-39`, `40+`, `>=60`
- 🥧 **Gráficos interactivos** — Barras y pastel con tooltips detallados
- 🔀 **Tabla cruzada** — Cruce de dos variables (Ej: Sexo × Diagnóstico)
- 👁️ **Vista de datos** — Previsualización completa del archivo cargado
- 🌙 **Modo oscuro** — Diseño adaptable claro/oscuro
- 📱 **Responsive** — Funciona en celular, tablet y computadora

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.10+ · FastAPI · Uvicorn |
| Análisis | Pandas · OpenPyXL |
| Frontend | HTML5 · TailwindCSS · JavaScript |
| Gráficos | Chart.js |
| Tipografía | Manrope · DM Serif Display |

---

## 🚀 Instalación

### 1. Clona el repositorio
```bash
git clone https://github.com/10godr/datatab-website.git
cd datatab-website
```

### 2. Instala las dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecuta el servidor
```bash
python main.py
```

### 4. Abre en el navegador
```
http://localhost:8000
```

---

## 📁 Estructura del Proyecto

```
datatab/
│
├── main.py                    ← Punto de entrada (limpio y simple)
├── requirements.txt
│
├── app/
│   ├── routes/
│   │   ├── upload.py          ← Rutas de carga de archivos
│   │   └── analysis.py        ← Rutas de análisis y API
│   │
│   ├── services/
│   │   ├── excel_service.py   ← Lectura y previsualización de archivos
│   │   └── stats_service.py   ← Cálculos estadísticos (frecuencias, cruces)
│   │
│   └── utils/
│       ├── file_handler.py    ← Manejo seguro de archivos (UUID)
│       └── validators.py      ← Validación de formatos y tamaño
│
├── templates/
│   ├── index.html             ← Página de inicio
│   └── analisis.html          ← Dashboard de análisis
│
└── uploads/                   ← Archivos subidos (generados automáticamente)
```

---

## 🖥️ Uso

1. **Sube** tu archivo Excel o CSV desde la página de inicio
2. **Selecciona** la columna que deseas analizar
3. (Opcional) **Define rangos** para variables numéricas
4. Presiona **Analizar** y obtén la tabla de frecuencias + gráfico
5. Usa la pestaña **Tabla Cruzada** para comparar dos variables

---

## 🔮 Mejoras Futuras

- [ ] Exportar resultados a Excel y PDF
- [ ] Soporte para múltiples hojas en un mismo Excel
- [ ] Histograma automático para variables numéricas
- [ ] Estadísticas descriptivas (media, mediana, desviación estándar)
- [ ] Publicación en la nube (Railway / Render)
- [ ] Autenticación de usuarios
- [ ] Historial de análisis

---

## 👨‍💻 Autor

**Diego Rodríguez**  
Estudiante de Ingeniería de Software  
[GitHub](https://github.com/10godr)

---

## 📄 Licencia

MIT License — libre para uso personal y académico.
