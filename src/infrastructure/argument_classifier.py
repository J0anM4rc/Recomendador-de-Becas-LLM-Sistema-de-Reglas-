import json
import re
from typing import Any, Dict, List, Optional
import logging

from src.domain.interfaces import LLMInterface, ScholarshipRepository
from src.infrastructure.llm_interface import GEMMA
from src.infrastructure.prolog_connector import PrologConnector


logger = logging.getLogger(__name__)

class ArgumentClassifier():
    def __init__(self, llm : LLMInterface = GEMMA(), repository: ScholarshipRepository = PrologConnector()):
        self.llm = llm
        self.repository = repository
        self.posibles_tipos_beca_criterio = []   
        # if self.prolog_connector:
        #     try:
        #         self.posibles_becas_ids = self.repository.get_all_scholarship_names()
        #         self.posibles_valores_criterios = self.repository.get_all_criteria(["organismo", "campo_estudio", "nivel", "ubicacion"])
        #     except Exception as e:
        #         raise ValueError(f"Error al cargar los IDs de becas o criterios desde Prolog: {e}")
        # else:
        #     raise ValueError("No se proporcionó ninguna base de conocimiento")
        self.beca_arg_prompt = """
Tu tarea es identificar y extraer los IDs de las becas mencionadas por el usuario.
**DEBES seleccionar EXCLUSIVAMENTE entre los siguientes IDs de beca si encuentras una coincidencia en el mensaje del usuario:**
---
{posibles_becas_list_str}
---
El usuario podría referirse a las becas por su nombre completo, parcial o apodo (ej. "la MEC", "Santander").
Mapea la mención al ID exacto. Si no se menciona ninguna beca de la lista, devuelve null.

**Instrucciones IMPORTANTES para la salida:**
- Devuelve **EXCLUSIVAMENTE** un objeto JSON válido: `{{"argumento": LISTA_DE_IDS_O_NULL}}`.
- `LISTA_DE_IDS_O_NULL` debe ser una lista de strings (IDs de beca) o `null`.

Mensaje del usuario:
\"\"\"{message}\"\"\"
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
  "action": "null",
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


        self.criterion_response = """
### 1 · Plantilla de salida (OBLIGATORIA)

{{
  "action": "modify | select | null",
  "field":  "criterio_o_null",
  "value":  "ID_OPCION_VALIDA_O_NULL"
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
  "action": "null",
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
  "action": "null",
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



    def _extract_json(self, text: str, key: str = None) -> Optional[Any]:
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
            return None

        try:
            data = json.loads(json_str)
            return data.get(key) if key else data
        except json.JSONDecodeError:
            logger.error(f"JSON decoding failed: {json_str}")
            return None
    def build_criteria_table(self,criteria_names: list[str]) -> str:
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
             
    def classify_criterion_response(self, available_options: Optional[List[str]] = None, context : str = None) -> dict:
        available_options = self.build_criteria_table(available_options)
        prompt = self.criterion_response.format(
            criteria_table=available_options,
            context=context or "",
        )
        raw_response = self.llm.generate(prompt)
        extracted = self._extract_json(raw_response)
        if not isinstance(extracted, dict):
            logger.error(f"No se extrajo JSON válido del LLM. Raw: {raw_response}")
            return {"action": None, "field": None, "value": None}

        result = {k: (None if extracted.get(k) in [None, "null"] else extracted.get(k))
                  for k in ["action", "field", "value"]}

        return result
    
    def extract_initial_criteria(self, context: Optional[str] = None) -> dict:
        """
        Extrae el criterio inicial del mensaje del usuario.
        Devuelve un dict con "action", "field" y "value".
        """
        available_options = self.build_criteria_table(["campo_estudio", "nivel", "financiamiento", "organismo"])
        prompt = self.initial_criteria.format(
            criteria_table=available_options,
            context=context or "",
        )
        raw_response = self.llm.generate(prompt)
        extracted = self._extract_json(raw_response)

        if not isinstance(extracted, dict):
            logger.error(f"No se extrajo JSON válido del LLM. Raw: {raw_response}")
            return {"action": None, "field": None, "value": None}

        result = {k: (None if extracted.get(k) in [None, "null"] else extracted.get(k))
                  for k in ["action", "field", "value"]}
        return result

    def detect_confirmation(self, context: str) -> dict:
        """
        Usa el LLM para interpretar si el usuario confirma ("si") o niega ("no").
        """
        available_options = self.build_criteria_table(["campo_estudio", "nivel", "financiamiento", "organismo"])
        prompt = self.interpret_confirmation.format(
            criteria_table=available_options,
            context=context or "",
        )

        raw_response = self.llm.generate(prompt)
        extracted_data = self._extract_json(raw_response)
        
        if not isinstance(extracted_data, dict):
            logger.warning(f"Confirmación no es objeto JSON: {extracted_data!r}")
            return {"confirmation": None}
        
        conf = extracted_data.get("confirmation")
        if conf == "yes":
            return {"confirmation": "yes"}
        if conf == "no":
            return {"confirmation": "no"}
        if conf is None or conf == "null":
            # Si no hay confirmación clara, devolvemos None
            return {"confirmation": None}
        
        # Cualquier otro valor lo consideramos ambiguo
        logger.warning(f"Valor inesperado de confirmation: {conf!r}")
        return {"confirmation": None}
        

    def classify_intent(self, message: str) -> str:
        prompt = self.intent_prompt.format(message=message)
        resp = self.llm.generate(prompt)
        intent_data = self._extract_json(resp) # Obtener el dict completo
        intent = intent_data.get("intencion") if isinstance(intent_data, dict) else None
        
        valid_intents = {"buscar_por_criterio", "info_beca", "explicar_termino", "general_qa", "navegacion_conversacion"}
        if intent in valid_intents:
            return intent
        else:
            logger.warning(f"Intent classification failed or returned invalid intent. Raw LLM resp: '{resp}'. Extracted: '{intent_data}'. Falling back to general_qa.")
            return "general_qa" # Fallback


    def extract_beca_argument(self, message: str) -> Optional[List[str]]:
        if not self.posibles_becas_ids:
            logger.debug("No hay posibles_becas_ids cargados para extraer argumentos de beca.")
            return None

        posibles_becas_list_str = "\n".join(f"- {beca_id}" for beca_id in self.posibles_becas_ids)
        prompt = self.beca_arg_prompt.format(
            posibles_becas_list_str=posibles_becas_list_str,
            message=message
        )
        resp = self.llm.generate(prompt)
        arg_data = self._extract_json(resp) # Obtener el dict completo
        arg = arg_data.get("argumento") if isinstance(arg_data, dict) else None

        if arg is None:
            return None
        if isinstance(arg, list):
            # Filtrar para asegurar que solo devolvemos IDs válidos
            return [item for item in arg if isinstance(item, str) and item in self.posibles_becas_ids]
        if isinstance(arg, str) and arg in self.posibles_becas_ids:
            return [arg]
        logger.warning(f"Extracted beca argument is not valid or not in list. Raw: {arg}")
        return None


    def extract_type_argument(self, message: str) -> Optional[List[str]]: 
        if not self.posibles_tipos_beca_criterio:
            logger.debug("No hay posibles_tipos_beca_criterio definidos para extraer argumentos.")
            return None

        posibles_tipos_list_str = "\n".join(f"- {tipo}" for tipo in self.posibles_tipos_beca_criterio)
        prompt = self.tipo_arg_prompt.format(
            posibles_tipos_list_str=posibles_tipos_list_str,
            message=message
        )
        resp = self.llm.generate(prompt)
        arg_data = self._extract_json(resp)
        arg = arg_data.get("argumento") if isinstance(arg_data, dict) else None

        if arg is None:
            return None
        if isinstance(arg, list):
            return [item for item in arg if isinstance(item, str) and item in self.posibles_tipos_beca_criterio]
        if isinstance(arg, str) and arg in self.posibles_tipos_beca_criterio:
            return [arg]
        logger.warning(f"Extracted type argument is not valid or not in list. Raw: {arg}")
        return None

    def interpret_guided_response(self, user_message: str, current_question: str, available_options: List[str]) -> Dict[str, Optional[str]]:
        """
        Usa el LLM para interpretar la respuesta del usuario en el flujo guiado.
        Devuelve un dict: {"chosen_option": "opcion_elegida" o None, "navigation_intent": "accion_nav" o None}
        """
        available_options_str = ", ".join(f"'{opt}'" for opt in available_options)
        
        prompt = self.guided_response_prompt.format(
            current_question=current_question,
            available_options_str=available_options_str,
            user_message=user_message
        )
        logger.debug(f"GUIDED_RESPONSE_PROMPT:\n{prompt}") # Descomentar para depurar el prompt
        raw_response = self.llm.generate(prompt)
        logger.debug(f"GUIDED_RESPONSE_LLM_RAW:\n{raw_response}") # Descomentar para depurar la respuesta del LLM

        extracted_data = self._extract_json(raw_response) # Devuelve el dict completo
        
        if isinstance(extracted_data, dict):
            chosen_option = None if extracted_data.get("chosen_option") == "null" else extracted_data.get("chosen_option")
            navigation_intent = None if extracted_data.get("navigation_intent") == "null" else extracted_data.get("navigation_intent")

            # Validar que la opción elegida (si existe) esté en las opciones disponibles
            if chosen_option is not None and chosen_option not in available_options:
                logger.warning(f"LLM chose an option ('{chosen_option}') not in available_options: {available_options}. Setting to None.")
                chosen_option = None # Invalidar si no está en la lista
            
            valid_navigation_intents = ["atras", None]
            if navigation_intent not in valid_navigation_intents:
                logger.warning(f"LLM returned an invalid navigation_intent: '{navigation_intent}'. Setting to None.")
                navigation_intent = None

            return {
                "chosen_option": chosen_option,
                "navigation_intent": navigation_intent,
            }
        else:
            logger.error(f"Failed to extract valid JSON from LLM for guided response. Raw: {raw_response}")
            return {"chosen_option": None, "navigation_intent": None} # Fallback seguro

