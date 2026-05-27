"""
Expansión de queries con sinónimos para mejorar recuperación del RAG.
"""

import re
from typing import Dict, List

# Diccionario de sinónimos/ambiguaciones
SYNONYMS: Dict[str, str] = {
    'sistemas': 'sistemas computacionales ISC ingenieria',
    'la carrera': 'ingenieria sistemas computacionales ISC reticula',
    'primer semestre': 'semestre 1',
    'segundo semestre': 'semestre 2',
    'tercer semestre': 'semestre 3',
    'cuarto semestre': 'semestre 4',
    'quinto semestre': 'semestre 5',
    'sexto semestre': 'semestre 6',
    'séptimo semestre': 'semestre 7',
    'septimo semestre': 'semestre 7',
    'octavo semestre': 'semestre 8',
    'noveno semestre': 'semestre 9',
    'servicio social': 'servicio social liberacion constancia 480 horas',
    'ss': 'servicio social liberacion constancia',
    'residencia': 'residencia profesional',
    'titulacion': 'titulacion opciones tesis ceneval',
    'beca': 'becas excelencia economico descuento',
    'dieta': 'dieta estudiante economico saludable nutricion sma',
    'comer sano': 'dieta estudiante saludable economico nutricion sma',
    'comer saludable': 'dieta estudiante saludable economico nutricion sma',
    'presupuesto': 'economico barato estudiante dieta lista compras',
    'bajo presupuesto': 'economico barato estudiante dieta lista compras',
    'poco dinero': 'economico barato estudiante dieta lista compras',
    'alimentacion': 'nutricion sma dieta alimentos saludable',
    'nutricion': 'nutricion sma dieta alimentos estudiante saludable',
    'smae': 'sistema mexicano alimentos equivalentes nutricion porciones calorias',
    'doña pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks local restaurante',
    'don pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks local restaurante',
    'menu doña pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks',
    'café tec': 'café tec cafeteria comida campus restaurante local menu',
    'cafe tec': 'café tec cafeteria comida campus restaurante local menu',
    'manos sucias': 'manos sucias comida rapida campus restaurante local menu',
    'coffee shop': 'coffee shop cafe campus restaurante local menu',
    'comida rapida': 'comedores locales campus doña pelos cafe tec manos sucias menu',
    'lugar para comer': 'comedores locales campus doña pelos cafe tec manos sucias restaurante',
    'reglamento': 'reglamento estudiantes tecnm normas derechos obligaciones',
    'derechos': 'reglamento estudiantes derechos obligaciones normas tecnm',
    'obligaciones': 'reglamento estudiantes derechos obligaciones normas tecnm',
    'sancion': 'reglamento estudiantes conductas sanciones disciplina tecnm',
    'conducta': 'reglamento estudiantes conductas prohibidas sanciones tecnm',
    'baja': 'reglamento estudiantes baja temporal definitiva reinscripcion tecnm',
    'equidad': 'reglamento estudiantes equidad genero derechos humanos tecnm',
    'tecnm': 'tecnm instituto tecnologico ciudad juarez itcj',
    'itcj': 'tecnm itcj instituto tecnologico ciudad juarez',
    'escuela': 'tecnm itcj instituto tecnologico ciudad juarez campus',
    'instituto': 'tecnm itcj instituto tecnologico ciudad juarez',
    'hola': 'bienvenida saludo',
    'constancia': 'tramite constancia estudios kardex creditos',
    'kardex': 'tramite constancia estudios kardex creditos',
    'credencial': 'tramite credencial estudiante tecnm',
    'inscripcion': 'tramite inscripcion reinscripcion tecnm',
    'reinscripcion': 'tramite reinscripcion inscripcion tecnm',
    'materia': 'reticula isc materia semestre clave creditos',
    'semestre': 'reticula isc semestre materias plan estudios',
    'prerrequisito': 'reticula isc prerequisitos materias plan',
    'prerequisito': 'reticula isc prerequisitos materias plan',
    'creditos': 'reticula isc creditos materias semestre plan',
    'plan estudios': 'reticula isc plan estudios materias semestre',
    'servicio social': 'servicio social liberacion constancia 480 horas tecnm',
    'residencia': 'residencia profesional tecnm',
    'titulacion': 'titulacion opciones tesis ceneval tecnm',
    'beca': 'becas excelencia economico descuento tecnm',
}

# Cache simple para expansiones frecuentes
_expansion_cache: Dict[str, str] = {}


def expand_query(query: str) -> str:
    """
    Expande sinonimos comunes para mejorar la recuperacion del RAG.
    Utiliza cache para queries repetidos.
    """
    if not query:
        return query
    
    cache_key = query.lower().strip()
    if cache_key in _expansion_cache:
        return _expansion_cache[cache_key]
    
    q_lower = query.lower()
    expansions = []
    
    for key, expansion in SYNONYMS.items():
        # Usar regex para match de palabra completa
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, q_lower):
            expansions.append(expansion)
    
    result = query
    if expansions:
        result = f"{query} {' '.join(expansions)}"
    
    # Guardar en cache (limitado a 1000 entries)
    if len(_expansion_cache) < 1000:
        _expansion_cache[cache_key] = result
    
    return result
