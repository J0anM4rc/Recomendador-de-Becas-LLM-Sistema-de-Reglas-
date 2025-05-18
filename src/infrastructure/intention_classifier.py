import json
import re
from typing import Any, Dict, List, Optional
import logging

from src.domain.interfaces import LLMInterface, IntentClassifierService
from src.application.services.prolog_connector import NoResultsError, PrologConnector, PrologConnectorError

logger = logging.getLogger(__name__)

class IntentionClassifier(IntentClassifierService):
    def __init__(self, llm : LLMInterface, prolog_connector: Optional[PrologConnector] = None):
        self.llm = llm
        self.prolog_connector = prolog_connector
        self.posibles_tipos_beca_criterio = []   
        self.unified_prompt = """
Eres un asistente experto en procesar solicitudes de usuarios sobre becas.
Tu tarea es analizar el mensaje del usuario y extraer la información solicitada.
Responde EXCLUSIVAMENTE con un objeto JSON válido que siga ESTRICTAMENTE la estructura detallada a continuación.
NO incluyas NINGÚN texto adicional, explicaciones, ni comentarios antes o después del objeto JSON. Tu única salida debe ser el objeto JSON.

TODOS los campos definidos en la estructura JSON son OBLIGATORIOS. Si un campo o subcampo no es aplicable para el mensaje del usuario o no se extrae información para él, su valor DEBE ser `null` en el JSON de salida. No omitas ningún campo.

Estructura JSON Requerida:
{{
  "intention": "...",            // Opciones: buscar_por_nombre, buscar_por_criterios, explicar_termino, navegacion_atras, navegacion_saltar, navegacion_elegir_criterio, navegacion_confirmar, general_qa
  "filters": {{
    "name": "TEXTO_O_NULL",       // Texto para buscar por nombre de beca. Si no se especifica, usa null.
    "organization": "ORGANISMO_O_NULL", // Organismo que financia la beca (ej. "público estatal", "privado"). Si no se especifica, usa null.
    "area": "AREA_O_NULL",         // Área de estudio (ej. "grado", "posgrado"). Si no se especifica, usa null.
    "education_level": "NIVEL_O_NULL", // Nivel educativo (ej. "máster", "doctorado"). Si no se especifica, usa null.
    "place": "LUGAR_O_NULL"        // Lugar de estudio o de la beca (ej. "España", "Valencia"). Si no se especifica, usa null.
  }},
  "explanation_term": "TEXTO_O_NULL", // Término específico que el usuario quiere que se explique. Si no aplica, usa null.
  "confirmation": "si" o "no", // Respuesta de confirmación del usuario (ej. "sí", "no"). Si no aplica, usa null.
  "error": "MENSAJE_ERROR_O_NULL"   // Mensaje de error si algo falló en tu análisis interno o si el mensaje es incomprensible. Si no hay error, usa null.
}}

Consideraciones para la intención y extracción de datos:

- `buscar_por_nombre`: El usuario quiere buscar una beca específica por su nombre propio o identificador textual.
    - Extrae el nombre en `filters.name`.
    - Ejemplo: "Busco información sobre la Beca Excelencia Global" -> `intention: "buscar_por_nombre"`, `filters.name: "Beca Excelencia Global"`.
    - Todos los demás campos de `filters`, `explanation_term`, `navigation`, `confirmation` serían `null`.
    
- `buscar_por_criterios`:
    El usuario quiere iniciar una búsqueda guiada de becas o está respondiendo a preguntas del sistema para filtrar becas (ej., especificando área, financiación, lugar).
    - Los filtros relevantes (`filters.area`, `filters.financing`, `filters.place`) se poblarán con la información extraída. `filters.name` y `filters.code` suelen ser `null` en este caso.
    - `navigation`, `explanation_term`, `confirmation` serían `null`.
    - Ejemplo: "Busco becas de arte en Italia" -> `intention: "navegar"`, `filters.area: "arte"`, `filters.place: "Italia"`.
    - Ejemplo: "Para máster" (en respuesta a "¿Nivel de estudios?") -> `intention: "navegar"`, `filters.area: "máster"` (o un campo específico si lo tuvieras, como `level`).

- `explicar_termino`: El usuario pide una explicación sobre un término, concepto, o tipo de beca.
    - Extrae el término o concepto clave en `explanation_term`.
    - Ejemplo: "¿Qué significa 'financiación completa'?" -> `intention: "explicar_termino"`, `explanation_term: "financiación completa"`.
    - Todos los campos de `filters`, `navigation`, `confirmation` serían `null`.
    
- `navegacion_atras`: El usuario indica que quiere volver atrás o quiere modificar un criterio ya respondido.
  - No extrae filtros ni otros campos; todos serán `null` excepto `intention`.

- `navegacion_saltar`: El usuario indica que quiere saltar o marcar cualquier paso/respuesta dentro del flujo guiado.
  - No extrae filtros ni otros campos; todos serán `null` excepto `intention`.

- `navegacion_confirmar`: El usuario responde afirmativa o negativamente a una pregunta de confirmación del sistema.
    - El campo `confirmation` se poblará con "si" o "no".
    - Todos los campos de `filters`, `explanation_term`, `navigation` serían `null`.
    - Ejemplo: "Sí, es correcto" -> `intention: "confirmacion"`, `confirmation: "si"`.
- navegacion_elegir_criterio: El usuario quiere elegir un criterio específico dentro de un flujo guiado.
    - Extrae el criterio elegido en `filters` (ej. `filters.area`, `filters.financing`, etc.).
    - Ejemplo: "Quiero una beca pública" -> `intention: "navegacion_elegir_criterio"`, `filters.organization: "público"`.

- `general_qa`: Preguntas generales sobre becas, el proceso, requisitos genéricos, que no constituyen una búsqueda activa, una petición de explicación de un término específico, ni una navegación.
    - Todos los campos de `filters`, `explanation_term`, `navigation`, `confirmation` serían `null`.
    - Ejemplo: "¿Qué documentos suelen pedir para las becas?" -> `intention: "general_qa"`.

Recuerda: Es CRUCIAL que el JSON de salida contenga SIEMPRE todos los campos (`intention`, `filters` (con `name`, `area`, `financing`, `place` dentro), `explanation_term`, `navigation`, `confirmation`, `error`), usando `null` como valor si no aplica.

Mensaje del usuario:
\"\"\"{message}\"\"\"

JSON de salida:
"""
        if self.prolog_connector:
            try:
                # Usaremos la consulta 'beca(Id)' para obtener todos los IDs de beca_X.
                query_ids = "beca(Id)."
                results_ids = self.prolog_connector._run_query(query_ids, ["Id"])
                self.posibles_becas_ids = sorted(list(set(item['Id'] for item in results_ids if 'Id' in item and isinstance(item['Id'], str))))
                logger.info(f"Cargados {len(self.posibles_becas_ids)} IDs de becas desde Prolog.")

                # Cargar posibles valores para criterios (organismo, campo_estudio, financiamiento, nivel, ubicacion)
                # Esto es un ejemplo, idealmente estos también se cargarían dinámicamente o se definirían mejor
                self.posibles_valores_criterios = {
                    "organismo": ["publico_estatal", "publico_local", "privado", "internacional", "otros"],
                    "campo_estudio": ["ciencias_tecnicas", "ciencias_sociales", "arte_humanidades", "salud", "otros"],
                    "financiamiento": ["completa", "parcial", "ayuda_transporte", "otros"],
                    "nivel": ["escolar", "postobligatoria_no_uni", "grado", "posgrado", "otros"],
                    "ubicacion": ["espana", "valencia", "europa", "cualquiera"] # 'cualquiera' es un valor especial
                }
                logger.info(f"Cargados posibles valores para criterios de búsqueda.")

            except Exception as e:
                logger.error(f"No se pudieron cargar los IDs de becas o criterios desde Prolog: {e}")
                self.posibles_becas_ids = []
                self.posibles_valores_criterios = {}
        else:
            logger.warning("No se proporcionó PrologConnector. IntentionClassifier operará sin listas predefinidas.")

        # Actualización del intent_prompt para naturalidad
        self.intent_prompt = """
Analiza el siguiente mensaje del usuario y clasifícalo estrictamente en UNA de las siguientes intenciones.
Considera el contexto de una conversación sobre becas.

1.  `buscar_por_criterio`: El usuario quiere iniciar o continuar una búsqueda de becas, o responde a una pregunta del sistema como parte de una búsqueda guiada.
    *   Peticiones explícitas: "buscar becas", "empecemos la búsqueda".
    *   Expresiones de necesidad: "necesito una beca para mi grado".
    *   Preguntas sobre disponibilidad: "¿qué becas hay para estudiar en Francia?".
    *   Recomendaciones basadas en criterios: "recomiéndame becas para un doctorado internacional".
    *   **Respuestas a preguntas directas del sistema durante la búsqueda guiada**:
        *   Si el sistema pregunta "¿Para qué nivel educativo?" y el usuario dice "Para grado", la intención es `guiado`.
        *   Si el sistema pregunta "¿Confirmas estos datos?" y el usuario dice "Sí, es correcto", la intención es `guiado` (o `confirmacion_positiva` si prefieres más granularidad).
    Ejemplos: "ayúdame a buscar", "necesito financiación", "para ingeniería", "un máster en Alemania", "sí, todo bien", "no, quiero cambiar algo".

2.  `info_beca`: Pregunta por información general, plazos, requisitos o enlace web de una beca específica ya nombrada o inferida del contexto.
    Ejemplos: "¿Qué sabes de beca_mec_general?", "Info sobre Beca Santander", "Cuéntame más sobre la beca Fulbright", "¿Cuándo abre la convocatoria de la MEC?", "¿Qué requisitos tiene la Erasmus Mundus?", "Dame el enlace de la beca UPV Deporte".

3.  `explicar_termino`: Pide una explicación sobre un tipo de beca, un criterio de selección, una forma de financiación, o un término relacionado con becas.
    Ejemplos: "¿Qué es mérito académico?", "Explícame qué son las becas completas", "¿Qué significa 'convocatoria abierta'?".

4.  `general_qa`: Preguntas generales sobre el proceso de solicitud, documentación, consejos, que NO expresan intención inmediata de búsqueda para el usuario actual.
    Ejemplos: "¿Qué documentos suelen pedir?", "¿Cómo es el proceso en general?".

5.  `navegacion_conversacion`: El usuario quiere controlar el flujo de la conversación de forma más explícita (retroceder, cancelar, reiniciar).
    Ejemplos: "atrás", "quiero volver al paso anterior", "cancela esto", "empecemos de nuevo", "olvídalo".

**Instrucciones de salida:**
Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la estructura: `{{ "intencion": "..." }}`
Mensaje del usuario:
\"\"\"{message}\"\"\"

JSON de salida:
"""

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
        # Prompt para extraer la opción elegida por el usuario en el flujo guiado
        self.guided_response_prompt = """
Analiza la respuesta del usuario a una pregunta específica dentro de un flujo de búsqueda de becas.
La pregunta actual del sistema fue: "{current_question}"
Las opciones válidas para esta pregunta son: {available_options_str}

El usuario podría:
1. Elegir una de las opciones válidas (o una paráfrasis de ella).
2. Indicar que quiere retroceder (ej: "atrás", "me equivoqué, el anterior").
3. Indicar que quiere omitir/no sabe/le da igual la opción actual (ej: "sáltalo", "no sé", "cualquiera", "no tengo preferencia").
4. Intentar cancelar la búsqueda actual (ej: "cancela", "olvídalo").
5. Dar una respuesta que no encaja en ninguna de las anteriores.

Extrae la opción elegida por el usuario si la respuesta se corresponde semánticamente con una de las opciones válidas.
Si el usuario quiere navegar (atrás, saltar/cualquiera, cancelar), indica esa intención de navegación.
Si la respuesta no es clara o no corresponde a una opción ni a una navegación clara, indica que no se entiende.

**Opciones válidas disponibles para el usuario (mapea la respuesta del usuario a uno de estos si es posible):**
{available_options_formatted_list}

**Instrucciones de salida:**
Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la siguiente estructura:
`{{ "chosen_option": "ID_OPCION_VALIDA_O_NULL", "navigation_intent": "VALOR_NAVEGACION_O_NULL" }}`

- `chosen_option`: Debe ser EXACTAMENTE una de las opciones válidas de la lista (ej: "grado", "publico_local") si el usuario eligió una. Si no eligió una opción válida, debe ser `null`.
- `navigation_intent`: Puede ser uno de: "atras", "saltar_omitir", "cancelar". Si no hay intención de navegación, debe ser `null`.

Si el usuario dice "me gustaría para grado", `chosen_option` sería "grado".
Si el usuario dice "la de ciencias técnicas", `chosen_option` sería "ciencias_tecnicas".
Si el usuario dice "mejor volvemos al anterior", `navigation_intent` sería "atras".
Si el usuario dice "no me importa", `navigation_intent` sería "saltar_omitir".
Si el usuario dice "mejor no seguimos", `navigation_intent` sería "cancelar".
Si el usuario dice "azul", y "azul" no es una opción válida, `chosen_option` sería `null` y `navigation_intent` sería `null`.

Mensaje del usuario:
\"\"\"{user_message}\"\"\"

JSON de salida:
"""
        # Prompt para interpretar la confirmación del usuario (sí/no)
        self.confirmation_interpretation_prompt = """
El sistema ha presentado un resumen de los datos recogidos y ha preguntado al usuario si son correctos.
Analiza la respuesta del usuario para determinar si está confirmando (sí) o rechazando/queriendo cambiar (no) los datos.

Ejemplos de confirmación (interpretar como "si"):
- "Sí"
- "Correcto"
- "Todo bien"
- "Adelante"
- "Perfecto"

Ejemplos de rechazo/cambio (interpretar como "no"):
- "No"
- "Incorrecto"
- "Quiero cambiar algo"
- "Espera, eso no está bien"
- "No, empecemos de nuevo"

Respuesta del usuario:
\"\"\"{user_message}\"\"\"

**Instrucciones de salida:**
Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la estructura:
`{{ "confirmation": "RESPUESTA_INTERPRETADA" }}`
Donde `RESPUESTA_INTERPRETADA` debe ser "si" o "no". Si la respuesta es ambigua, tiende a "no" para seguridad.

JSON de salida:
"""


        # Ejemplo de tipos para explicacion_termino. Podría cargarse de Prolog también.
        if not self.posibles_tipos_beca_criterio:
            self.posibles_tipos_beca_criterio = [
                "merito_academico", "deportivo", "artistico", "necesidad_economica",
                "completa", "parcial", "manutencion", "matricula", "investigacion",
                "movilidad", "excelencia_academica", "publico_estatal", "publico_local",
                "privado", "internacional", "ciencias_tecnicas", "ciencias_sociales",
                "arte_humanidades", "salud", "postobligatoria_no_uni", "grado", "posgrado"
            ]
        self.tipo_arg_prompt = """
        Tienes estos tipos de beca/criterio/término disponibles para explicar:
        \"\"\"{posibles_tipos_list_str}\"\"\"

        Analiza este mensaje del usuario y extrae cuál(es) de esos tipos menciona que quiere que se le explique.
            - Si menciona uno, devuelve su nombre exacto. Ejemplo: "merito académico" → ["merito_academico"].
            - Si menciona varios, devuelve una lista con todos los nombres.
            - Si no menciona ninguno de la lista, devuelve null.

        **Instrucciones de salida:**
        Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la siguiente estructura:
        `{{ "argumento": [...] }}`  // lista de tipos o null

        Mensaje del usuario:
        \"\"\"{message}\"\"\"

        JSON de salida:
        """
    # ... (resto de __init__ como estaba)
    def _load_scholarship_ids_from_prolog(self) -> List[str]:
        # Este método ya estaba, pero lo muevo aquí para agrupar y asegurar que usa la consulta correcta
        if not self.prolog_connector:
            return []
        try:
            # Consulta para obtener todos los IDs de becas declaradas con beca/1
            query = "beca(Id)."
            results = self.prolog_connector._run_query(query, ["Id"])
            ids = [item['Id'] for item in results if 'Id' in item and isinstance(item['Id'], str)]
            return sorted(list(set(ids)))
        except NoResultsError:
            logger.info("No se encontraron IDs de becas en Prolog con la consulta 'beca(Id)'.")
            return []
        except PrologConnectorError as e:
            logger.error(f"Error de PrologConnector al cargar IDs de becas: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al cargar IDs de becas desde Prolog: {e}")
            return []


    def classify_all(self, message: str) -> Dict[str, Any]:
        prompt = self.unified_prompt.format(message=message)
        raw = None
        try:
            # 1. Llamada única al LLM
            raw = self.llm.generate(prompt)
            data = self._extract_json(raw)
            if not isinstance(data, dict):
                raise ValueError("No dict returned")
        except Exception as e:
            logger.error(f"Unified classify failed ({e}). Raw: {raw}")
            # Fallback al método existente
            return self.classify(message)

        # 2. Saneamiento y valores por defecto
        intent = data.get("intention") or "general_qa"
        filters = data.get("filters") or {}
        for f in ("name","code","area","financing","place"):
            filters.setdefault(f, None)

        nav = data.get("navigation")
        if nav not in ("atras","saltar","cancelar", None):
            nav = None

        conf = data.get("confirmation")
        if conf not in ("si","no", None):
            conf = None

        err = data.get("error")
        if err is not None and not isinstance(err, str):
            err = None

        return {
            "intention": intent,
            "filters": filters,
            "navigation": nav,
            "confirmation": conf,
            "error": err
        }
        
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
          
          
    def classify(self, message: str, current_question: Optional[str] = None, available_options: Optional[List[str]] = None, is_confirming: bool = False) -> dict:
        """
        Clasificación principal. Ahora puede tomar contexto del flujo guiado.
        """
        # # Si estamos en el flujo guiado (se proporciona current_question y options)
        # if current_question and available_options and not is_confirming:
        #     guided_interpretation = self.interpret_guided_response(message, current_question, available_options)
        #     # Si el LLM encontró una opción o una intención de navegación, se considera parte del flujo guiado
        #     if guided_interpretation["chosen_option"] or guided_interpretation["navigation_intent"]:
        #         return {
        #             "intencion": "respuesta_guiada", # Nueva pseudo-intención para el flujo
        #             "chosen_option": guided_interpretation["chosen_option"],
        #             "navigation_intent": guided_interpretation["navigation_intent"],
        #             "argumento": None # Argumento principal no aplica aquí
        #         }
        
        # # Si estamos en una fase de confirmación
        # if is_confirming:
        #     confirmation_status = self.interpret_confirmation_response(message)
        #     return {
        #         "intencion": "respuesta_confirmacion", # Nueva pseudo-intención
        #         "confirmation_status": confirmation_status, # "si" o "no"
        #         "argumento": None
        #     }

        # Si no es una respuesta guiada directa ni confirmación, hacer clasificación general de intención
        intent = self.classify_intent(message)
        argument = None

        # if intent == "info_beca":
        #     argument = self.extract_beca_argument(message)
        # elif intent == "explicacion_termino": # Coincidir con el nombre del prompt y la intención
        #     argument = self.extract_type_argument(message) # Usar el método renombrado
        # # La intención "guiado" ahora es más para iniciar el flujo o para respuestas que el LLM no pudo mapear a una opción/navegación directa.
        # # La intención "navegacion_conversacion" es para comandos de navegación más explícitos fuera del 'interpret_guided_response'.

        return {"intencion": intent, "argumento": argument}

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
        available_options_formatted_list = "\n".join(f"- '{opt}'" for opt in available_options)
        
        prompt = self.guided_response_prompt.format(
            current_question=current_question,
            available_options_str=available_options_str,
            available_options_formatted_list=available_options_formatted_list,
            user_message=user_message
        )
        # logger.debug(f"GUIDED_RESPONSE_PROMPT:\n{prompt}") # Descomentar para depurar el prompt
        raw_response = self.llm.generate(prompt)
        # logger.debug(f"GUIDED_RESPONSE_LLM_RAW:\n{raw_response}") # Descomentar para depurar la respuesta del LLM

        extracted_data = self._extract_json(raw_response) # Devuelve el dict completo
        
        if isinstance(extracted_data, dict):
            chosen_option = extracted_data.get("chosen_option")
            navigation_intent = extracted_data.get("navigation_intent")

            # Validar que la opción elegida (si existe) esté en las opciones disponibles
            if chosen_option is not None and chosen_option not in available_options:
                logger.warning(f"LLM chose an option ('{chosen_option}') not in available_options: {available_options}. Setting to None.")
                chosen_option = None # Invalidar si no está en la lista
            
            valid_navigation_intents = ["atras", "saltar_omitir", "cancelar", None]
            if navigation_intent not in valid_navigation_intents:
                logger.warning(f"LLM returned an invalid navigation_intent: '{navigation_intent}'. Setting to None.")
                navigation_intent = None

            return {
                "chosen_option": chosen_option,
                "navigation_intent": navigation_intent
            }
        else:
            logger.error(f"Failed to extract valid JSON from LLM for guided response. Raw: {raw_response}")
            return {"chosen_option": None, "navigation_intent": None} # Fallback seguro

    def interpret_confirmation_response(self, user_message: str) -> str:
        """
        Usa el LLM para interpretar si el usuario confirma ("si") o niega ("no").
        """
        prompt = self.confirmation_interpretation_prompt.format(user_message=user_message)
        raw_response = self.llm.generate(prompt)
        extracted_data = self._extract_json(raw_response)

        if isinstance(extracted_data, dict):
            confirmation = extracted_data.get("confirmation")
            if confirmation in ["si", "no"]:
                return confirmation
            else:
                logger.warning(f"LLM returned invalid confirmation value: '{confirmation}'. Defaulting to 'no'.")
                return "no" # Default seguro si la respuesta no es clara
        else:
            logger.error(f"Failed to extract valid JSON from LLM for confirmation. Raw: {raw_response}. Defaulting to 'no'.")
            return "no" # Fallback seguro