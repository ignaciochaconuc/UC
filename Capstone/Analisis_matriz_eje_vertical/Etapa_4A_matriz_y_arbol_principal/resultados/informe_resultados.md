# Etapa 4A — matriz perforada y árbol principal (premodelo)

No modifica la etapa 3C. No es FEA: sin identificación verificada del apoyo axial, unión y cargas laterales, las tensiones de flexión de la matriz y deformaciones estructurales no están identificadas.

## Geometría derivada del CAD y CSV

- perforaciones: 102
- espesor_m: 0.036
- radio_exterior_m: 0.1
- radio_central_m: 0.025
- radio_centros_min_m: 0.04702993137354125
- radio_centros_max_m: 0.07986495810429003
- paso_min_entre_centros_m: 0.012421999999999989
- ligamento_min_entre_agujeros_6mm_m: 0.0064219999999999885
- ligamento_min_bocas_9mm_m: 0.0034219999999999893
- margen_exterior_boca_9mm_m: 0.01563504189570997
- margen_centro_boca_9mm_m: 0.01752993137354125
- area_bruta_m2: 0.031415926535897934
- area_neta_simplificada_m2: 0.026568449071408883
- porcentaje_huecos_pasantes_area: 15.429999999999998
- masa_cilindrica_simplificada_kg: 7.50824370758015
- advertencia: Masa y área sin chavetero ni avellanados; no son resistencia neta bajo flexión

## Historial simultáneo: extremos

- **max_fuerza_total**: paso 1097, ángulo 274.25°; Fz=14.071 kN, T=88.924 N·m,  Mx=-1.511 N·m, My=131.557 N·m, |M|=131.566 N·m
- **max_torque**: paso 377, ángulo 94.25°; Fz=14.071 kN, T=88.924 N·m,  Mx=1.511 N·m, My=-131.557 N·m, |M|=131.566 N·m
- **max_momento_normales**: paso 1077, ángulo 269.25°; Fz=12.864 kN, T=79.063 N·m,  Mx=1.183 N·m, My=153.797 N·m, |M|=153.802 N·m
- **max_VM_eje_d35**: paso 377, ángulo 94.25°; Fz=14.071 kN, T=88.924 N·m,  Mx=1.511 N·m, My=-131.557 N·m, |M|=131.566 N·m

## Eje: tensiones nominales por diámetro hipotético

```text
 diametro_mm  sigma_axial_max_MPa  tau_torsion_max_MPa  sigma_VM_max_sin_flexion_MPa  VM_si_todo_M_transmitido_MPa  angulo_VM_condicional_deg  sigma_flexion_max_MPa  angulo_VM_critico_deg  F_en_instante_VM_N  T_en_instante_VM_Nm  giro_por_metro_rad_m_en_Tmax                                                   leyenda  n_nominal_1045  n_hipotesis_todo_M_1045  n_nominal_4140  n_hipotesis_todo_M_4140
          35            14.625092            10.562940                     23.422647                     52.732257                      88.50              36.538994                  94.25        14070.987477            88.923966                      0.007640 eje sólido liso; sin flexión, chaveteros, fatiga o apoyos       15.796677                 7.016578       40.132099                17.825901
          40            11.197336             7.076344                     16.601334                     36.573926                      88.50              24.478272                  94.25        14070.987477            88.923966                      0.004479 eje sólido liso; sin flexión, chaveteros, fatiga o apoyos       22.287366                10.116497       56.621957                25.701370
          45             8.847278             4.969943                     12.344040                     26.570603                     268.25              17.191872                  94.25        14070.987477            88.923966                      0.002796 eje sólido liso; sin flexión, chaveteros, fatiga o apoyos       29.973980                13.925164       76.150110                35.377443
          50             7.166295             3.623088                      9.525549                     20.017739                     268.25              12.532875                  94.25        14070.987477            88.923966                      0.001834 eje sólido liso; sin flexión, chaveteros, fatiga o apoyos       38.842904                18.483606       98.681972                46.958351
```


La columna que añade flexión es una hipótesis de transferencia del MOMENTO EXTERNO completo a la misma sección, sin apoyos ni fuerzas de correa; NO es un esfuerzo interno resuelto por equilibrio de árbol.

NOTA: la sección real y transmisión de empuje axial no están determinadas. Sin presión sobre asiento, cargas de correa, diagrama de momentos/rodamientos, ni Kt/Kf no puede obtenerse el factor de seguridad final del árbol.

## Matriz: pendientes para FEM sólido / placa

1. Definir si carga normal va a tope axial, brida, pernos o rodamiento de empuje.
2. Definir contacto matriz--eje: ajuste, chaveta y retención axial; restringir solo GDL reales.
3. Considerar avellanados Ø9, agujeros Ø6, espesor 36 mm, hueco Ø50 y chavetero.
4. Mallar 3D con refinamiento de radios y puentes; aplicar cargas por agujero en pasos 3C correlacionados; verificar convergencia de desplazamientos y tensiones lejos de singularidades.
5. Verificar fluencia/fatiga, deformación de superficie, contacto de cubo, reacción axial y torsión en chaveta.

FUENTES MATERIALES CONDICIONALES: [('SAE 1045 +QT (>40 a 100 mm, Atlas)', 370000000.0, 'https://atlassteels.com.au/documents/Atlas1045.pdf'), ('SAE 4140 / 6115 +QT (barra >25 a <60 mm, Ovako)', 940000000.0, 'https://steelnavigator.ovako.com/steel-grades/42crmo4/')]
