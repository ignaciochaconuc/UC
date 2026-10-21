"""5F: controles de integración, sin ejecutar modelos históricos."""
import math

ESTADOS={'verificado','condicionado_modelo','propuesta','pendiente','incompatible'}
UNIDADES={'1','mm','rpm','kW','N','N m','grado','h/dia','m/s'}


def parametro(nombre,valor,unidad,estado,fuente,escenario,nota=''):
    if unidad not in UNIDADES or estado not in ESTADOS or not fuente or not escenario:
        raise ValueError('Unidad, estado, fuente y escenario explícitos requeridos')
    if isinstance(valor,bool) or not isinstance(valor,(float,int)) or not math.isfinite(valor):
        raise ValueError('Valor numérico finito requerido')
    return dict(parametro=nombre,valor=valor,unidad=unidad,estado=estado,
                fuente=fuente,escenario=escenario,nota=nota)


def verificar_utilizacion(potencia_diseno,capacidad,utilizacion):
    if not all(math.isfinite(v) and v>0 for v in (potencia_diseno,capacidad,utilizacion)):
        raise ValueError('Potencias y utilización positivas requeridas')
    if not math.isclose(potencia_diseno/capacidad,utilizacion,rel_tol=1e-10):
        raise ValueError('Utilización inconsistente; no confundir margen y utilización')
    return utilizacion<=1


def verificar_historial(equilibrio,condicional,esperados):
    if len(equilibrio)!=esperados or len(condicional)!=esperados or esperados!=1440:
        raise ValueError('Se requieren los 1440 estados completos')
    claves=('paso','tiempo_s','angulo_grados')
    if len({r['paso'] for r in equilibrio})!=esperados:
        raise ValueError('Estados duplicados')
    for a,b in zip(equilibrio,condicional):
        if any(a[k]!=b[k] for k in claves):
            raise ValueError('Escenarios/estados no correlacionados')
        if a['escenario']!=b['escenario'] or a['escenario']!='historial_3c_inclinacion':
            raise ValueError('No mezclar escenario nominal con 3C')
    return True


def estado_cierre(matriz):
    if not matriz or any(r['estado'] not in ESTADOS for r in matriz):
        raise ValueError('Matriz de estados inválida')
    bloqueos=[r['verificacion'] for r in matriz if r['esencial_aprobacion'] and r['estado']!='verificado']
    return {'predimensionamiento_documentado':True,'listo_redaccion_ingenieria_basica':True,
            'transmision_aprobada':not bloqueos,'bloqueos_aprobacion':bloqueos,
            'autorizado_fabricacion':False,'motor_seleccionado':None}
