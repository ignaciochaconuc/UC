#!/usr/bin/env pvpython
"""Capturas comparables del campo instantáneo final con el lector integrado."""
from pathlib import Path
from paraview.simple import *
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'resultados';OUT.mkdir(exist_ok=True)
import paraview.simple as pvs
pvs._DisableFirstRenderCameraReset()
view=CreateView('RenderView');view.ViewSize=[1800,450]
view.Background=[1,1,1];view.UseColorPaletteForBackground=0
view.CameraParallelProjection=1;view.OrientationAxesVisibility=0
view.CameraPosition=[50,10,200];view.CameraFocalPoint=[50,10,1.05];view.CameraViewUp=[0,1,0];view.CameraParallelScale=13.5
for re in [100,1000,10000,100000]:
    reader=OpenFOAMReader(FileName=str(ROOT/f'Re{re}/Re{re}.foam'))
    reader.MeshRegions=['internalMesh'];reader.CellArrays=['U','p','vorticity']
    if 'Decomposepolyhedra' in reader.ListProperties(): reader.Decomposepolyhedra=0
    reader.UpdatePipelineInformation();view.ViewTime=400;reader.UpdatePipeline(400)
    cp=CellDatatoPointData(Input=reader);cp.UpdatePipeline(400)
    grad=cp
    display=Show(grad,view);display.Representation='Surface'
    text=Text();td=Show(text,view);td.Color=[0,0,0];td.FontSize=16;td.WindowLocation='Upper Center'
    for field,component,label,low,high,preset in [
        ('U','Magnitude','Velocidad [m/s]',0,1.8,'Viridis (matplotlib)'),
        ('p',None,'Presión cinemática [m²/s²]',-1,1.5,'Cool to Warm'),
        ('vorticity','Z','Vorticidad z [1/s]',-2,2,'Cool to Warm')]:
        if component:ColorBy(display,('POINTS',field,component))
        else:ColorBy(display,('POINTS',field))
        lut=GetColorTransferFunction(field);lut.ApplyPreset(preset,True);lut.RescaleTransferFunction(low,high)
        display.SetScalarBarVisibility(view,True)
        bar=GetScalarBar(lut,view);bar.Title=label;bar.ComponentTitle='';bar.TitleColor=[0,0,0];bar.LabelColor=[0,0,0];bar.WindowLocation='Lower Center';bar.Orientation='Horizontal';bar.ScalarBarLength=.35;bar.TitleFontSize=13;bar.LabelFontSize=11
        text.Text=f'Re = {re} | t = 400 s | Campo instantáneo'
        view.CameraPosition=[50,10,200];view.CameraFocalPoint=[50,10,1.05];view.CameraParallelScale=13.5
        Render(view);SaveScreenshot(str(OUT/f'Re{re}_{field}.png'),view,ImageResolution=[1800,450])
        display.SetScalarBarVisibility(view,False)
    Delete(text);Hide(grad,view);Delete(cp);Delete(reader)
    print('Capturas terminadas Re',re,flush=True)
Delete(view)
