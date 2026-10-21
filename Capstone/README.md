# Peletizadora de matriz plana

El proyecto se organiza por subsistema:

```text
Capstone/
├── Simulación_peletizadora/       # Contacto, eje transversal y rodamientos; etapas 1–4A
├── Analisis_matriz_eje_vertical/  # Aporte del otro integrante; etapas propias 4A–4D
├── Transmision/                  # Próximo trabajo: transmisión mecánica
└── README.md
```

El archivo `boceto_ingenieria_basica.pdf` mostrado en la estructura de referencia
no está presente en la carpeta al organizarla. Su ubicación prevista es esta raíz.

## Simulación de contacto, eje transversal y rodillos

[Simulación_peletizadora/README.md](Simulación_peletizadora/README.md) contiene
las instrucciones y los resultados de las etapas 1–4A. Su carpeta `datos/`
conserva `agujeros_matriz.csv`, entrada geométrica utilizada por sus códigos.

Desde esa carpeta:

```powershell
python -m pytest -q
```

## Matriz y eje vertical

[Analisis_matriz_eje_vertical/README.md](Analisis_matriz_eje_vertical/README.md)
indexa los códigos, informes y resultados del otro integrante. Este aporte se
trasladó desde `Simulación_peletizadora/datos/datos/` conservando sus archivos.
Su numeración 4A–4D pertenece a ese subsistema: su 4A de matriz/eje vertical es
distinta de la 4A de rodamientos de los rodillos.

## Transmisión

[Transmision/README.md](Transmision/README.md) delimita el próximo trabajo.
Los estudios condicionales de correas recibidos permanecen en el aporte del otro
integrante para conservar su trazabilidad.
