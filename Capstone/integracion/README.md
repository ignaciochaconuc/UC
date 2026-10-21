# Integración — Auditoría documental6A

Desde la raíz del repositorio:

```powershell
python Capstone/integracion/auditoria_6a.py
python -m pytest Capstone/integracion/test_auditoria_6a.py -q
```

Solo se leen los tres subsistemas y se generan archivos en
`Capstone/resultados_integracion/etapa_6a/`. No se importan ni ejecutan sus
modelos. Los controles verifican fuentes, contenido de auditoría y SHA256;
no calculan resistencia ni ejecutan FEM. El esquema y alcance de6B se
mantienen en `camino_cargas_6a.md` y se copian al paquete de resultados.

Los CSV clasifican16 grupos de componentes según evidencia, acciones,
geometría, estado y prioridad. No son una aprobación de diseño ni una lista
de piezas confirmadas: se distingue expresamente propuesta/inferencia.
Los hashes cubren todos los archivos de los subsistemas excepto cachés;
los históricos permanecen intactos.
