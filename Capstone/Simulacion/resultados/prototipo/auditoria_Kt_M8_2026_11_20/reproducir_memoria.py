"""Revisión documental: lee resultados congelados, nunca importa ni ejecuta 3C.

Ejecutar desde cualquier directorio: python <ruta a este archivo>.
Solo escribe dentro de esta revisión; el manifiesto histórico no se regenera.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

D = Path(__file__).resolve().parent
S = D.parents[2]
REPO = S.parents[1]
SERIE = S / 'resultados/prototipo/acoplado_m8_2026_11_20/serie_M8x1.25_h4mm.csv'


def verificar_historicos():
    manifest = json.loads((D / 'historicos_sha256.json').read_text(encoding='utf-8'))
    cambios = [p for p, h in manifest.items()
               if not (REPO / p).is_file()
               or hashlib.sha256((REPO / p).read_bytes()).hexdigest() != h]
    if cambios:
        raise ValueError('Históricos alterados: ' + repr(cambios))
    return {'archivos_verificados': len(manifest), 'alterados': 0}


def escribir_json(nombre, data):
    (D / nombre).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                     allow_nan=False) + '\n', encoding='utf-8')


def escribir_csv(nombre, rows):
    with (D / nombre).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def factor_estatico(sy_pa, sigma_raiz_pa, kt_raiz):
    if not all(math.isfinite(x) and x > 0 for x in (sy_pa, sigma_raiz_pa, kt_raiz)):
        raise ValueError('Entradas finitas y positivas, unidades Pa; Kt adimensional')
    if kt_raiz < 1:
        raise ValueError('El Kt de diagnóstico debe ser >= 1')
    return sy_pa / (sigma_raiz_pa * kt_raiz)


def convertir_kt(kt_raiz, d_raiz_m, d_mayor_m):
    if not all(math.isfinite(x) and x > 0 for x in (kt_raiz, d_raiz_m, d_mayor_m)):
        raise ValueError('Geometría y factor positivos')
    if d_raiz_m >= d_mayor_m or kt_raiz < 1:
        raise ValueError('Se requiere diámetro de raíz menor que el mayor, Kt>=1')
    return kt_raiz * (d_mayor_m / d_raiz_m)**3


def leer_base():
    with SERIE.open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1440 or len({r['paso'] for r in rows}) != 1440:
        raise ValueError('Historial incompleto')
    if not all(r['convergio'] == 'True' and float(r['capa_m']) == .004
               and r['varilla'] == 'M8x1.25' for r in rows):
        raise ValueError('Escenario distinto de M8, capa 4 mm, convergido')
    c = json.loads((S / 'configuraciones/acoplado_m8.json').read_text(encoding='utf-8'))
    v = next(x for x in c['varillas'] if x['nombre'] == 'M8x1.25')
    m = json.loads((S / 'configuraciones/resistencia_m8.json').read_text(encoding='utf-8'))
    material = next(x for x in m['clases'] if x['clase'] == '8.8')
    return rows, c, v, material


def main():
    antes = verificar_historicos()
    rows, c, v, material = leer_base()
    crit = max(rows, key=lambda r: float(r['sigma_nominal_max_pa']))
    sigma = float(crit['sigma_nominal_max_pa'])
    sy = material['Sy_min_pa']
    d, mayor = v['nucleo_referencia_m'], v['nominal_m']
    ratio = (mayor / d)**3
    sigma_mayor = sigma / ratio
    kt_lim = sy / sigma
    momentos = sigma * math.pi * d**3 / 32
    casos = []
    for variable in ('fuerza_total_n', 'torque_total_nm', 'flecha_max_m', 'sigma_nominal_max_pa'):
        r = max(rows, key=lambda x: float(x[variable]))
        casos.append(dict(maximo_de=variable, paso=int(r['paso']), angulo_grados=float(r['angulo_grados']),
                          fuerza_total_n=float(r['fuerza_total_n']), torque_total_nm=float(r['torque_total_nm']),
                          flecha_max_m=float(r['flecha_max_m']), sigma_nominal_max_pa=float(r['sigma_nominal_max_pa']),
                          x_sigma_max_desde_extremo_m=float(r['x_sigma_max_m'])))
    escribir_csv('casos_correlacionados.csv', casos)
    sensibilidad = []
    for kt in (1., 1.25, 1.5, 1.75, 2., kt_lim, 2.5, 3.):
        sensibilidad.append(dict(Kt_base_raiz=kt, Kt_equivalente_base_mayor=convertir_kt(kt,d,mayor),
            sigma_local_elastica_pa=kt*sigma, n_y_condicional=factor_estatico(sy,sigma,kt),
            origen='Umbral n_y=1 calculado' if kt==kt_lim else
                   'Antecedente EP2 no calibrado' if kt in (1.,1.5,2.5) else 'Punto de diagnóstico matemático',
            rango_fisico_validado=False, aprobacion=False,
            interpretacion='Extrapolación elástica más allá de fluencia; no predice colapso' if kt>kt_lim
                            else 'Comprobación de flexión condicionada; no aprobación'))
    escribir_csv('sensibilidad_Kt_sin_seleccion.csv', sensibilidad)
    escribir_csv('umbrales_no_prescriptivos.csv', [dict(n_objetivo_hipotetico=n,
        Kt_raiz_maximo=kt_lim/n, requisito_del_proyecto=False) for n in (1.,1.5,2.)])
    geo = [
        ('Diámetro mayor nominal',8,'mm','Nominal M8; producto no medido'),
        ('Paso',1.25,'mm','Nominal; confirmar ficha y tolerancia del producto'),
        ('Ángulo de flancos',60,'grados','Perfil básico ISO; no medición de la pieza'),
        ('Diámetro de núcleo usado en 3C',6.466,'mm','Referencia tabulada; no diámetro mínimo certificado'),
        ('Radio mínimo 0,125P, antecedente ISO 965-1:2013',.125*1.25,'mm',
         'Solo antecedente indexado, norma reemplazada; no radio real ni requisito 2026 verificado'),
        ('Radio de referencia H/6, raíz plenamente redondeada',math.sqrt(3)*1.25/12,'mm',
         'Geometría ideal publicada; no radio confirmado ni Kt seleccionado'),
        ('Radio real y perfil completo de raíz',None,'mm','PENDIENTE ficha/perfilometría'),
        ('Tolerancias d, d2, d3 y recubrimiento',None,'mm','PENDIENTE norma de producto y certificado'),
        ('Fase de la hélice en las secciones críticas',None,'grados','PENDIENTE geometría fabricada'),
        ('Salida de rosca, transición y filetes',None,'mm','PENDIENTE montaje definitivo'),
        ('Primer filete engranado y longitud efectiva',None,'mm','PENDIENTE tuercas/inserto/apoyos'),
        ('Precarga y reparto de contacto en fijaciones',None,'N','PENDIENTE; empotramiento solo hipotético'),
    ]
    escribir_csv('geometria_y_datos_faltantes.csv', [dict(parametro=a,valor=b,unidad=u,estado=e) for a,b,u,e in geo])
    escribir_csv('auditoria_EP2.csv', [
        dict(fuente='Entrega_2.pdf p.19-20, A.4.5/A.4.6',hallazgo='Kt 1/1,5/2,5 son barrido paramétrico; no radio ni tabla de rosca específica',aplicacion='No seleccionar Kt M8'),
        dict(fuente='Entrega_2.pdf p.20, ec.35-38',hallazgo='Marin, Se inicial, Kf=1+q(Kt-1), Goodman; no determinan Kt geométrico',aplicacion='Procedimiento de fatiga, no valores heredables'),
        dict(fuente='Entrega_2.pdf p.12 ref.[11]',hallazgo='Budynas y Nisbett, Shigley 9a edición española, 2012',aplicacion='Bibliografía general; no gráfico identificable para Kt 1,5/2,5'),
        dict(fuente='Simulación_peletizadora/estructural/resistencia_fatiga.py, ENTALLAS',hallazgo='Kt1,5 q0,70 y Kt2,5 q0,90 declarados no calibrados/no validados',aplicacion='Solo sensibilidad; q tampoco transferible'),
    ])
    fatiga = [
        ('Geometría y fijaciones reales','Radio/perfil/tolerancias; filete crítico, engrane, transición, precarga y contacto','Seleccionar Kt compatible con nominal de raíz'),
        ('Producto y fabricación','Certificado 8.8; acero/tratamiento, roscado cortado o laminado y secuencia, zincado, tensiones residuales','Sut y q/Kf representativos; condición superficial'),
        ('Resistencia cíclica','Curva S-N o Se justificable del producto, temperatura, ambiente, confiabilidad y acabado','No adoptar automáticamente 0,5Sut ni Kf comercial ya corregido'),
        ('Servicio','Espectro, ciclos, vida objetivo, arranque/atasco y carga manual; rigidez real ABS','Historial 3C es un ciclo de modelo, no espectro de vida validado'),
        ('Tratamiento de tensiones','Historial firmado en la misma fibra, media/amplitud correlacionadas; plasticidad si corresponde','No usar envolvente positiva ni flexión rotativa alternante por defecto'),
    ]
    escribir_csv('requisitos_cierre_fatiga.csv',[dict(tema=a,datos_necesarios=b,consecuencia=c) for a,b,c in fatiga])
    resumen = dict(revision='auditoria_Kt_M8_2026_11_20',tipo='Memoria, sin nueva simulación',
        escenario=dict(varilla='M8x1.25',clase_candidata='8.8',capa_m=.004,E_pa=c['material']['E_referencia_pa'],
                       presion_pa=c['presion_pa'],mu_efectivo=c['mu_efectivo'],doble_empotramiento='Hipótesis no validada físicamente'),
        estados=len(rows),sigma_nominal_raiz_pa=sigma,diamenor_referencia_m=d,diamayor_nominal_m=mayor,
        Sy_min_condicionado_pa=sy,momento_resultante_correspondiente_nm=momentos,
        I_raiz_m4=math.pi*d**4/64,Z_raiz_m3=math.pi*d**3/32,
        sigma_nominal_base_mayor_pa=sigma_mayor,conversion_Kt_mayor_sobre_Kt_raiz=ratio,
        Kt_raiz_seleccionado=None,Kf_seleccionado=None,factor_seguridad_estatico_definitivo=None,
        factor_seguridad_fatiga_definitivo=None,n_y_sin_concentracion=kt_lim,
        Kt_raiz_umbral_inicio_fluencia_flexion=kt_lim,Kt_mayor_umbral=kt_lim*ratio,
        alcance_umbral='Cribado elástico de flexión uniaxial local; no verificación multiaxial de la unión',
        critico_sigma={k:float(crit[k]) for k in ['paso','angulo_grados','x_sigma_max_m','fuerza_total_n','torque_total_nm','flecha_max_m']},
        fuerza_max_n=max(float(r['fuerza_total_n']) for r in rows),torque_vertical_max_nm=max(float(r['torque_total_nm']) for r in rows),
        flecha_max_m=max(float(r['flecha_max_m']) for r in rows),
        fuentes_configuracion='Solo lectura de configuraciones y CSV históricos; no se llama ModeloAcoplado',
        aprobado=False,conclusion='Kt único no identificable; clase8.8 candidata y M8 preferente no equivalen a seguridad aprobada',
        conservacion=antes)
    escribir_json('resumen.json',resumen)
    escribir_json('conservacion_historica.json',verificar_historicos())
    print(json.dumps(resumen,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
