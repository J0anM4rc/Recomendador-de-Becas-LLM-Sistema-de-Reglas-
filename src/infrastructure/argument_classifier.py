import json
import re
from typing import Any, Dict, List, Optional
import logging

from src.domain.interfaces import LLMInterface, ScholarshipRepository
from src.infrastructure.prolog_connector import PrologConnector


logger = logging.getLogger(__name__)

class ArgumentClassifier():
    def __init__(self, llm : LLMInterface, repository: ScholarshipRepository = PrologConnector()):
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
        # Prompt para extraer la opción elegida por el usuario en el flujo guiado
        self.guided_response_prompt = """
Estás ayudando a interpretar la respuesta del usuario dentro de un flujo de búsqueda de becas.

La pregunta actual fue: "{current_question}"
Opciones válidas: {available_options_str}

Siempre tiene prioridad la opcion `cualquiera` si el usuario la menciona o no entiendes lo que quiere elegir
El usuario podría:
- Elegir una opción (por nombre exacto, similar o referirse a una opcion de cualquier otra forma). 
- Indicar que quiere navegar: 
  - “atrás” para volver a la pregunta anterior,
  - “cancelar” si quiere abandonar la búsqueda.
- Tener una duda sobre la pregunta o el funcionamiento del flujo de búsqueda de becas.

Devuelve SOLO este JSON:
{{ 
  "chosen_option": "ID_OPCION_VALIDA_O_NULL", 
  "navigation_intent": "atras | cancelar | null" 
  "posible_intent": "general_qa" | null"
}}

Si eligió una opción, la navegación es null.
Si no eligió opción clara ni navegación, pon ambos en null.

Mensaje del usuario:
\"\"\"{user_message}\"\"\"

JSON de salida:
"""
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
        if current_question and available_options:
            word_count = len(message.strip().split())
            if word_count <= 4:
                ordinal_map = {
                    r"\bprimera|primer[o|a]\b": 0,
                    r"\bsegunda|segund[o|a]\b": 1,
                    r"\btercera|tercer[o|a]\b": 2,
                    r"\bcuarta|cuart[o|a]\b": 3,
                    r"\bquinta|quint[o|a]\b": 4,
                    r"\bsexta|sext[o|a]\b": 5,
                }

                for pattern, index in ordinal_map.items():
                    if re.search(pattern, message, re.IGNORECASE):
                        if index < len(available_options):
                            return {
                                "chosen_option": available_options[index],
                                "navigation_intent": None,
                                "argumento": None
                            }
        # Si estamos en el flujo guiado (se proporciona current_question y options)
        if current_question and available_options and not is_confirming:
            guided_interpretation = self.interpret_guided_response(message, current_question, available_options)
            # Si el LLM encontró una opción o una intención de navegación, se considera parte del flujo guiado
            if guided_interpretation["chosen_option"] or guided_interpretation["navigation_intent"]:
                return {
                    "chosen_option": guided_interpretation["chosen_option"],
                    "navigation_intent": guided_interpretation["navigation_intent"],
                    "argumento": None # 
                }
        
        # Si estamos en una fase de confirmación
        if is_confirming:
            confirmation_status = self.interpret_confirmation_response(message)
            return {
                "intencion": "respuesta_confirmacion", # Nueva pseudo-intención
                "confirmation_status": confirmation_status, # "si" o "no"
                "argumento": None
            }
        return {"error": "No se pudo clasificar la intención del mensaje."}

        # Si no es una respuesta guiada directa ni confirmación, hacer clasificación general de intención
        # intent = self.classify_intent(message)
        # argument = None

        # if intent == "info_beca":
        #     argument = self.extract_beca_argument(message)
        # elif intent == "explicacion_termino": # Coincidir con el nombre del prompt y la intención
        #     argument = self.extract_type_argument(message) # Usar el método renombrado
        # # La intención "guiado" ahora es más para iniciar el flujo o para respuestas que el LLM no pudo mapear a una opción/navegación directa.
        # # La intención "navegacion_conversacion" es para comandos de navegación más explícitos fuera del 'interpret_guided_response'.

        # return {"intencion": intent, "argumento": argument}

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