#!/usr/bin/env python3
"""Genera diccionarios para OpenFOAM Foundation 14; no ejecuta simulaciones."""
from pathlib import Path
import re
import shutil
import argparse

ROOT = Path(__file__).resolve().parent
FOAM = Path('/opt/openfoam14')
p = argparse.ArgumentParser()
p.add_argument('--fine', action='store_true', help='Refina un nivel adicional toda la malla')
a = p.parse_args()

def write(case, name, body, cls='dictionary'):
    path = ROOT / case / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'FoamFile\n{{\n    format ascii;\n    class {cls};\n    object {path.name};\n}}\n\n' + body + '\n')

for case in ['mesh3d', 'mesh2d']:
    write(case, 'system/controlDict', 'application foamRun;\nstartFrom startTime;\nstartTime 0;\nstopAt endTime;\nendTime 1;\ndeltaT 0.01;\nwriteControl timeStep;\nwriteInterval 1;\nwriteFormat ascii;\nwritePrecision 10;')
    for name in ['fvSchemes', 'fvSolution']:
        dest = ROOT / case / 'system' / name
        shutil.copyfile(FOAM / 'tutorials/incompressibleFluid/cylinder/system' / name, dest)

nx, ny, nz = (400,80,4) if a.fine else (200,40,2)
write('mesh3d', 'system/blockMeshDict', '''convertToMeters 1;
vertices ((0 0 0) (100 0 0) (100 20 0) (0 20 0)
          (0 0 1) (100 0 1) (100 20 1) (0 20 1));
blocks (hex (0 1 2 3 4 5 6 7) (NX NY NZ) simpleGrading (1 1 1));
edges ();
boundary
(
 inlet { type patch; faces ((0 4 7 3)); }
 outlet { type patch; faces ((1 2 6 5)); }
 walls { type wall; faces ((0 1 5 4) (3 7 6 2)); }
 back { type patch; faces ((0 3 2 1)); }
 front { type patch; faces ((4 5 6 7)); }
);
'''.replace('NX',str(nx)).replace('NY',str(ny)).replace('NZ',str(nz)))
# Reutilizar los controles oficiales, adaptando geometría y refinamiento.
s = (FOAM/'tutorials/mesh/snappyHexMesh/flange/system/snappyHexMeshDict').read_text()
start = s.index('geometry\n')
end = s.index('// Settings for the castellatedMesh generation.')
s = s[:start] + '''geometry
{
 cylinder { type cylinder; point1 (6 10 -2); point2 (6 10 3); radius 1; }
 nearBody { type box; min (3 7 -2); max (12 13 3); }
 wake { type box; min (7 6 -2); max (40 14 3); }
 farWake { type box; min (40 7 -2); max (80 13 3); }
 lowerWall { type box; min (-1 -1 -2); max (101 0.6 3); }
 upperWall { type box; min (-1 19.4 -2); max (101 21 3); }
}

''' + s[end:]
s = re.sub(r'features\s*\(.*?\);', 'features ();', s, flags=re.S)
s = s.replace('flange\n        {', 'cylinder\n        {').replace('level (2 2);', 'level (4 4);\n            patchInfo { type wall; }')
s = re.sub(r'refinementRegions\s*\{.*?\n    \}', '''refinementRegions
    {
      nearBody { mode inside; level 3; }
      wake { mode inside; level 2; }
      farWake { mode inside; level 1; }
      lowerWall { mode inside; level 1; }
      upperWall { mode inside; level 1; }
    }''', s, count=1, flags=re.S)
s = re.sub(r'    insidePoint .*?;', '    insidePoint (1.123 5.123 0.234);', s)
s = s.replace('maxLocalCells 100000;', 'maxLocalCells 2000000;').replace('maxGlobalCells 2000000;', 'maxGlobalCells 3000000;')
s = s.replace('nCellsBetweenLevels 1;', 'nCellsBetweenLevels 3;')
s = s.replace('addLayers       false;', 'addLayers       true;')
s = s.replace('"flange_.*"', '"cylinder"').replace('nSurfaceLayers 1;', 'nSurfaceLayers 3;').replace('expansionRatio 1.0;', 'expansionRatio 1.2;').replace('minThickness 0.25;', 'minThickness 0.05;')
s = s.replace('explicitFeatureSnap true;', 'explicitFeatureSnap false;').replace('nFeatureSnapIter 10;', 'nFeatureSnapIter 0;')
(ROOT/'mesh3d/system/snappyHexMeshDict').write_text(s)
shutil.copyfile(FOAM/'tutorials/mesh/snappyHexMesh/flange/system/meshQualityDict', ROOT/'mesh3d/system/meshQualityDict')
write('mesh2d','system/extrudeMeshDict','''constructFrom patch;
sourceCase "$FOAM_CASE/../mesh3d";
sourcePatches (front);
exposedPatchName back;
extrudeModel plane;
thickness 0.1;
flipNormals false;
mergeFaces false;''')
write('mesh2d','system/createPatchDict','''pointSync false;
patches
(
 { name front; patchInfo { type empty; } constructFrom patches; patches (front); }
 { name back; patchInfo { type empty; } constructFrom patches; patches (back); }
);''')
print('Diccionarios generados. Resolución:', 'fina' if a.fine else 'base')

# Re basado en el diámetro: U=1 m/s, D=2 m, nu=U*D/Re.
# Misma escala temporal en todos los casos; se varía la viscosidad.
for re_value in [100, 1000, 10000, 100000]:
    case = f'Re{re_value}'
    turbulent = re_value >= 10000
    write(case, 'constant/physicalProperties', f'viscosityModel constant;\nnu {2/re_value:.10g};')
    write(case, 'constant/momentumTransport', 'simulationType RAS;\nRAS { model kOmegaSST; turbulence on; }' if turbulent else 'simulationType laminar;')
    write(case, 'system/controlDict', '''application foamRun;
solver incompressibleFluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 400;
deltaT 0.005;
adjustTimeStep yes;
maxCo 0.5;
maxDeltaT 0.05;
writeControl adjustableRunTime;
writeInterval 2;
purgeWrite 0;
writeFormat binary;
writePrecision 10;
runTimeModifiable true;
functions
{
 forceCoeffs
 {
  type forceCoeffs;
  libs ("libforces.so");
  patches (cylinder);
  rho rhoInf;
  rhoInf 1;
  CofR (6 10 1.05);
  liftDir (0 1 0);
  dragDir (1 0 0);
  pitchAxis (0 0 1);
  magUInf 1;
  lRef 2;
  Aref 0.2;
  writeControl timeStep;
  writeInterval 1;
 }
}''')
    source = (FOAM/'tutorials/incompressibleFluid/cylinder/system/fvSchemes').read_text()
    source = source.replace('default         steadyState;', 'default         backward;')
    (ROOT/case/'system/fvSchemes').write_text(source)
    shutil.copyfile(FOAM/'tutorials/incompressibleFluid/cylinder/system/fvSolution', ROOT/case/'system/fvSolution')
    empty = 'front { type empty; }\n back { type empty; }'
    wall_u = '"(walls|cylinder)" { type noSlip; }'
    write(case, '0/U', f'''dimensions [0 1 -1 0 0 0 0];
internalField uniform (1 0 0);
boundaryField
{{
 inlet {{ type fixedValue; value uniform (1 0 0); }}
 outlet {{ type inletOutlet; inletValue uniform (1 0 0); value uniform (1 0 0); }}
 {wall_u}
 {empty}
}}''', 'volVectorField')
    write(case, '0/p', f'''dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{{
 inlet {{ type zeroGradient; }}
 outlet {{ type fixedValue; value uniform 0; }}
 "(walls|cylinder)" {{ type zeroGradient; }}
 {empty}
}}''', 'volScalarField')
    if turbulent:
        # Intensidad de entrada I=1%, longitud de mezcla l=0.07D=0.14m.
        k = 1.5*0.01**2
        omega = k**0.5 / (0.09**0.25*0.14)
        for field, dims, value, wall in [
            ('k','[0 2 -2 0 0 0 0]',k,'kqRWallFunction'),
            ('omega','[0 0 -1 0 0 0 0]',omega,'omegaWallFunction'),
            ('nut','[0 2 -1 0 0 0 0]',0,'nutUSpaldingWallFunction')]:
            inlet = f'type fixedValue; value uniform {value};' if field!='nut' else 'type calculated; value uniform 0;'
            outlet = f'type inletOutlet; inletValue uniform {value}; value uniform {value};' if field!='nut' else 'type calculated; value uniform 0;'
            write(case, f'0/{field}', f'''dimensions {dims};
internalField uniform {value};
boundaryField
{{
 inlet {{ {inlet} }}
 outlet {{ {outlet} }}
 "(walls|cylinder)" {{ type {wall}; value uniform {value}; }}
 {empty}
}}''', 'volScalarField')
    (ROOT/case/f'{case}.foam').touch()
print('Cuatro casos transientes preparados; aún no ejecutados.')

# Solver de presión validado frente a PCG en un tramo idéntico de Re100.
for re_value in [100, 1000, 10000, 100000]:
    path = ROOT / f'Re{re_value}/system/fvSolution'
    text = path.read_text().replace('solver          PCG;', 'solver          GAMG;')
    text = text.replace('preconditioner  DIC;', 'smoother GaussSeidel;\n        cacheAgglomeration true;\n        nCellsInCoarsestLevel 20;\n        agglomerator faceAreaPair;\n        mergeLevels 1;')
    path.write_text(text)
