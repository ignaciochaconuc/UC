# Análisis de matriz y eje vertical

Aporte del otro integrante, antes ubicado en
`Simulación_peletizadora/datos/datos/`. Se conservan los códigos, resultados,
copias de fuentes, informes y nombres originales de las etapas.

| Carpeta | Contenido | Instrucciones originales |
|---|---|---|
| `Etapa_4A_matriz_y_arbol_principal/` | Resultantes sobre matriz y análisis nominal del eje vertical | [README.txt](Etapa_4A_matriz_y_arbol_principal/README.txt) |
| `Etapa_4B_matriz_arbol_condicional/` | Verificaciones condicionales de eje y transmisión | [README.md](Etapa_4B_matriz_arbol_condicional/README.md) |
| `Etapa_4C_apoyos_union/` | Apoyos y unión de la matriz | [README.md](Etapa_4C_apoyos_union/README.md) |
| `Etapa_4D_FEM_preliminar/` | Modelo FEM preliminar y convergencia | [README.md](Etapa_4D_FEM_preliminar/README.md) |

Las rutas internas de 4B–4D se resuelven desde sus propios archivos. Sus carpetas
`fuentes/`, `datos/` y `resultados/` se mantienen junto al código correspondiente.
Las copias de fuentes son históricas; moverlas no las sincroniza automáticamente.

La 4A recibe la ruta del proyecto de contacto mediante `--proyecto`. Desde
`Etapa_4A_matriz_y_arbol_principal/`, la ruta actual es:

```powershell
python simulacion_matriz_eje_4A.py --proyecto "../../Simulación_peletizadora" --salida resultados
```

**Compatibilidad de datos pendiente:** `_leer()` en esa simulación exige una
fuerza máxima 3C de `14070,987476941267 N` con tolerancia `0,001 N`, mientras
que la serie actual del proyecto alcanza aproximadamente `14071,128 N`.
La ejecución contra la serie actual puede detenerse por esa comprobación.
Antes de recalcular este aporte debe confirmarse qué versión de la serie 3C
corresponde utilizar. La reorganización conserva esa comprobación y los
resultados originales; no modifica modelos ni ajusta tolerancias físicas.

Comprobaciones de los resultados recibidos, desde cada carpeta respectiva:

```powershell
python test_etapa4a.py
python test_etapa_4B.py
python validar_4D.py
```

La última validación construye una malla de comprobación y requiere las
dependencias indicadas en el código FEM. Los dos primeros archivos contienen
aserciones ejecutadas directamente, en vez de funciones de prueba de pytest.
