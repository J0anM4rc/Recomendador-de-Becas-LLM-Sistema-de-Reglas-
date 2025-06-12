import json
import re
from typing import List, Optional
import logging
from domain.ports import LLMInterface, ScholarshipRepository, SlotsExtractorService
from infrastructure.exceptions import JSONExtractionError, IntentMismatchError

logger = logging.getLogger(__name__)

class SlotsExtractor(SlotsExtractorService):
    def __init__(self, llm : LLMInterface , repository: ScholarshipRepository):
        self.llm = llm
        self.repository = repository
        self.posibles_tipos_beca_criterio = []
        if self.repository:
            try:
                self.posibles_becas_ids = self.repository.get_all_scholarship_names()
                self.posibles_valores_criterios = self.repository.get_all_criteria(["organismo", "campo_estudio", "nivel", "ubicacion"])
            except Exception as e:
                raise ValueError(f"Error al cargar los IDs de becas o criterios desde Prolog: {e}")
        else:
            raise ValueError("No se proporcionó ninguna base de conocimiento")
        
        self.beca_arg_prompt = """
Tu tarea es identificar y extraer el ID de las becas mencionadas por el usuario.
**DEBES seleccionar EXCLUSIVAMENTE entre los siguientes IDs de beca si encuentras una coincidencia en el mensaje del usuario:**
---
{posibles_becas_list_str}
---
El usuario podría referirse a las becas por su nombre completo, parcial o apodo.
Mapea la mención al ID exacto. Si no se menciona ninguna beca de la lista, devuelve null.

**Instrucciones IMPORTANTES para la salida:**
- Devuelve **EXCLUSIVAMENTE** un objeto JSON válido: `{{"argumento": ID_O_NULL}}`.

--------------------------------------------------------------------
### 3 · Ejemplos de uso
**Ejemplo A —**
Asistente: Los requisitos para la beca llamada <strong>Beca ejemplo</strong> son:

 • <strong>Nota media</strong>: Aprobado general (5.0), varía por rama

...
Usuario: Y los de la beca de deporte de la upv
```json
{{
    "argumento": "beca_upv_deporte"
}}

**Ejemplo B **
Mensaje:
Usuario: de la beca de transporte
```json
{{
    "argumento": "beca_gv_transporte"
}}

**Ejemplo C **
Asistente:
Usuario: dame los requisitos de la beca
```json
{{
    "argumento": null
}}
---------------------------------------------------------------------
Mensaje del usuario:
\"\"\"{context}\"\"\"
JSON de salida:
"""
        self.interpret_confirmation= """
### 1 · Plantilla de salida (OBLIGATORIA)
{{
    "confirmation": "yes | no"
}}

--------------------------------------------------------------------
### 2 · Reglas de interpretación
1. **Confirmación**
    - Si el mensaje del usuario indica una afirmación clara (ej. "sí", "correcto", "vale") ⇒ `"confirmation": "yes"` .
2. **Negación**
    - Si el mensaje del usuario indica una negación clara (ej. "no", "incorrecto", "no es eso") ⇒ `"confirmation": "no"`.
3. **Ambigüedad**
    - Si el mensaje no es claro o no contiene una afirmación/negación clara ⇒ devuelve `"confirmation": "null"`.
--------------------------------------------------------------------
### 3 · Ejemplos de uso
**Ejemplo A — Confirmación**
Mensaje:
Usuario: Dale
```json
{{
    "confirmation": "yes"
}}

**Ejemplo B — Confirmación**
Mensaje:
Usuario: Si
```json
{{
    "confirmation": "yes"
}}

**Ejemplo C — Negación**
Mensaje:
Usuario: No, no es eso
```json
{{
    "confirmation": "no"
}}

**Ejemplo C — Negación**
Mensaje:
Usuario: Cambio el financiamiento a cualquiera
```json
{{
    "confirmation": "no"
}}

--------------------------------------------------------------------
Mensaje del usuario:
\"\"\"\n
{context}
\n\"\"\"

JSON de salida:

"""
        self.initial_criteria = """
### 1 · Plantilla de salida (OBLIGATORIA)
{{
    "action": "select | null",
    "field":  "criterio_o_null",
    "value":  "ID_OPCION_VALIDA_O_NULL"
}}
--------------------------------------------------------------------
### 2 · Tabla de criterios y valores permitidos
| field            | valores válidos (ID exacto)                              |
{criteria_table}
|------------------|----------------------------------------------------------|
Si el `value` propuesto **no** aparece en la columna del `field` elegido,
responde con los tres `null`.
--------------------------------------------------------------------

### 3 · Reglas de interpretación

1. **Selección de criterio**
    - Si el usuario **elige** claramente una de las opciones (nombre    
        exacto, equivalente claro o número de opcion en el mensaje del asistente) ⇒
        `"action": "select"`, `"field"` según la tabla, `"value"` opción válida.
2. **Ambigüedad**   
    - Si no queda claro lo que quiere o no menciona valores de la tabla ⇒
        devuelve todo `null`.
--------------------------------------------------------------------

### 4 · Check-list antes de responder 

1. ¿`action` ∈ {{ select, null}}?  
2. Si `action` ≠ null:  
   - ¿`field` ∈ {{organismo, nivel, campo_estudio}}?  
   - ¿`value` está en la columna correcta?  
3. Si falla cualquier punto → devuelve los tres `null`.
--------------------------------------------------------------------
### 5 · Ejemplos de uso
**Ejemplo A — Selección**
Mensaje:
Usuario: Quiero buscar un beca para mi grado

```json
{{
  "action": "select",
   "field": "nivel",
   "value": "grado"
}}

**Ejemplo B — Sin Selección**
Mensaje:
Usuario: Quiero buscar un beca
```json
{{
  "action": null,
    "field": null,
    "value": null
}}

**Ejemplo B — Sin Selección**
Mensaje:
Usuario: Quiero encontrar una beca para ingeniería informática
```json
{{
  "action": "select",
    "field": "campo_estudio",
    "value": "ciencias_tecnicas"
}}
--------------------------------------------------------------------
Mensaje del usuario:
\"\"\"\n
{context}
\n\"\"\"

JSON de salida:

"""
        self.criterion_response = """
### 1 · Plantilla de salida (OBLIGATORIA)

{{
  "action": "modify | select | null",
  "field":  "criterio_o_null",
  "value":  "OPCION_VALIDA_O_NULL"
}}


--------------------------------------------------------------------
### 2 · Tabla de criterios y valores permitidos

| field            | valores válidos (ID exacto)                              |
|------------------|----------------------------------------------------------|
{criteria_table}

Si el `value` propuesto **no** aparece en la columna del `field` elegido,
responde con los tres `null`.

--------------------------------------------------------------------
### 3 · Reglas de interpretación

1. **Pregunta**  
   - Si el mensaje acaba en “?” o empieza por “qué”, “cómo”, “cuándo”,  
     “por qué”, etc. ⇒ devuelve `null` en las tres claves.

2. **Selección de criterio**  
   - Si el usuario **elige** claramente una de las opciones (nombre
     exacto, equivalente claro o número de opcion en el mensaje del asistente) ⇒  
     `"action": "select"`, `"field"` según la tabla, `"value"` opción válida.

3. **Modificación de criterio**  
   - Si el usuario quiere **cambiar** un valor ya elegido ⇒  
     `"action": "modify"`, `"field"` afectado, `"value"` nuevo valor.

4. **Ambigüedad**  
   - Si no queda claro lo que quiere o no menciona valores de la tabla ⇒  
     devuelve todo `null`.

5. **“otro” vs “cualquiera”**  
   - Cuando se diga “otro” y pueda significar “lo que sea”, interpreta
     como `"cualquiera"` (no como `"otros"`), a menos que el contexto lo
     desambigue claramente.

--------------------------------------------------------------------
### 4 · Detección de frases de CAMBIO

Patrones típicos → acción **modificar**  
• “cambia … a …” · “cambia … por …”  
• “no, quiero ...” · “era …”
• “pasa de … a …” · “quiero cambiar … a …”  
El valor que sigue a “a/por” es el **nuevo** `value`.  
Nunca devuelvas el valor antiguo.

--------------------------------------------------------------------
### 5 · Check-list antes de responder 

1. ¿`action` ∈ {{modify, select, null}}?  
2. Si `action` ≠ null:  
   - ¿`field` ∈ {{organismo, nivel, campo_estudio}}?  
   - ¿`value` está en la columna correcta?  
3. Si falla cualquier punto → devuelve los tres `null`.

--------------------------------------------------------------------
### 6 · Ejemplos de uso

**Ejemplo A — Selección**

Mensaje:  
asistant: ¿En qué área de estudios te interesan las becas?
user: Pon posgrado para nivel

Salida:  
```json
{{
  "action": "modify",
  "field": "nivel",
  "value": "posgrado"
}}
Ejemplo B — Modificación

Mensaje:
asistant: ¿En qué área de estudios te interesan las becas?
user: Cambia de local a estatal

Salida:

{{
  "action": "modify",
  "field": "organismo",
  "value": "publico_estatal"
}}
Ejemplo C — Pregunta

Mensaje:
¿En qué consiste exactamente un doctorado?

Salida:

{{
  "action": null,
  "field": null,
  "value": null
}}
Ejemplo D — Ambigüedad “otro” / “cualquiera”

Mensaje:
asistant: ¿En qué área de estudios te interesan las becas?
user : Pon cualquier campo de estudio

Salida:

{{
  "action": "select",
  "field": "campo_estudio",
  "value": "cualquiera"
}}
Ejemplo E — Valor no válido

Mensaje:
asistant: ¿En qué área de estudios te interesan las becas?
user: Cambia organismo a lunar
Salida:

json

{{
  "action": null,
  "field": null,
  "value": null
}}

--------------------------------------------------------------------
Mensaje del usuario:
\"\"\"\n
{context}
\n\"\"\"


JSON de salida:

"""



    def _extract_json(self, text: str, key: str = None) -> dict:
        """
        Extrae el primer bloque JSON bien formado del texto.
        Si key se proporciona, devuelve data[key], si no, devuelve el dict completo.
        """
        def extract_balanced_json(text: str) -> Optional[str]:
            start = text.find("{")
            if start == -1:
                return None

            open_braces = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    open_braces += 1
                elif text[i] == "}":
                    open_braces -= 1
                    if open_braces == 0:
                        return text[start:i+1]
            return None  # No cerrado correctamente

        # Prioridad a bloques delimitados con ```json ... ```
        match_block = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match_block:
            json_str = match_block.group(1)
        else:
            json_str = extract_balanced_json(text)

        if not json_str:
            logger.warning(f"No JSON found in LLM response: {text}")
            raise JSONExtractionError("No JSON found in LLM response")

        try:
            data = json.loads(json_str)
            return data.get(key) if key else data
        except json.JSONDecodeError:
            logger.error(f"JSON decoding failed: {json_str}")
            raise JSONExtractionError("Failed to decode JSON from LLM response")
    def _build_criteria_table(self,criteria_names: list[str]) -> str:
        """
        Devuelve las filas Markdown:
        | **organismo** | internacional · publico_estatal · publico_local |
        """
        rows = []
        for crit in criteria_names:
            try:
                opts = self.repository.get_criteria(crit)
            except Exception as e:
                logger.warning(f"No se pudieron obtener opciones de {crit}: {e}")
                opts = []

            opts_md = " · ".join(opts) if opts else "(sin opciones)"
            rows.append(f"| **{crit}** | {opts_md} |")

        return "\n".join(rows) 
    def _validate_field_value(self, field: str, value: str) -> bool:
        """
        Valida si el campo y valor proporcionados son válidos.
        """
        if field not in ["organismo", "nivel", "campo_estudio", "ubicacion"]:
            logger.warning(f"Invalid field: {field}")
            return False
        
        valid_values = self.repository.get_criteria(field)
        if value not in valid_values:
            logger.warning(f"Invalid value '{value}' for field '{field}'. Valid values: {valid_values}")
            return False
        
        return True
        
    def extract_criterion(self, available_options: Optional[List[str]] = None, context : str = None, use_initial_prompt : bool = False) -> dict:
        """ Clasifica la respuesta del usuario para seleccionar o modificar un criterio.
        Si `use_initial_prompt` es True, usa el prompt inicial para la primera selección.
        """
        
        available_options = available_options or self._build_criteria_table(["campo_estudio", "nivel", "ubicacion", "organismo"])
        
        # 1) Selecciona el template y formatea el prompt
        template = (
            self.initial_criteria if use_initial_prompt
            else self.criterion_response
        )
        prompt = template.format(
            criteria_table=available_options,
            context=context or "",
        )
        
        # 2) Genera la respuesta del LLM y extrae el JSON
        raw_response = self.llm.generate(prompt)
        extracted = self._extract_json(raw_response)

        field = extracted.get("field").lower() if extracted.get("field") else None
        value = extracted.get("value").lower() if extracted.get("value") else None
        # 3) Validación de la respuesta extraída
        if self._validate_field_value(field, value):
            return { 
                "action": extracted.get("action").lower(),
                "field": field,
                "value": value
            }
        elif extracted.get("error"):
            logger.error(f"Error en la extracción: {extracted.get('error')}")
            raise IntentMismatchError(f"Error en la intención esperada: {extracted.get('error')}")
        else:
            logger.warning(f"Invalid field or value in extracted data: {extracted}")
            raise ValueError(f"Invalid field or value in extracted data: {extracted}")
            
    def extract_confirmation(self, context: str) -> dict:
        """
        Usa el LLM para interpretar si el usuario confirma ("si") o niega ("no").
        """
        available_options = self._build_criteria_table(["campo_estudio", "nivel", "financiamiento", "organismo"])
        prompt = self.interpret_confirmation.format(
            criteria_table=available_options,
            context=context or "",
        )
        raw_response = self.llm.generate(prompt)
        extracted_data = self._extract_json(raw_response)
         
        conf = extracted_data.get("confirmation")
        if conf == "yes":
            return {"confirmation": "yes"}
        elif conf == "no":
            return {"confirmation": "no"}
        elif extracted_data.get("error"):
            logger.warning(f"Error en la extracción de confirmación: {extracted_data.get('error')}")
            raise IntentMismatchError(f"Error en la intención esperada: {extracted_data.get('error')}")
        else:
            logger.warning(f"Valor inesperado de confirmation: {conf!r}")
            raise ValueError(f"Valor de confirmación inesperado  : {conf!r}")
        
    def extract_scholarship(self, context: str) -> Optional[List[str]]:
        if not self.posibles_becas_ids:
            logger.debug("No hay posibles_becas_ids cargados para extraer argumentos de beca.")
            return None

        posibles_becas_list_str = "\n".join(f"- {beca_id}" for beca_id in self.posibles_becas_ids)
        prompt = self.beca_arg_prompt.format(
            posibles_becas_list_str=posibles_becas_list_str,
            context=context or ""
        )
        resp = self.llm.generate(prompt)
        arg_data = self._extract_json(resp) # Obtener el dict completo
        
        if not isinstance(arg_data, dict):
            logger.error(f"No se extrajo JSON válido del LLM. Raw: {resp}")
            return {"argumento": None}
        
        arg = None if arg_data.get("argumento") in [None, "null"] else arg_data.get("argumento")
        return {"argumento": arg} 

    def extract(self, text):
        raise NotImplementedError("Este método no está implementado en SlotsExtractor. Usa extract_scholarship, extract_criterion o extract_confirmation según corresponda.")
