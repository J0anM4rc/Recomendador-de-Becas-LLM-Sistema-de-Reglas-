import json
import re
from typing import Any, Dict, List, Optional
import logging

from src.domain.interfaces import LLMInterface, IntentClassifierService
from src.infrastructure.llm_interface import GEMMA

logger = logging.getLogger(__name__)

class IntentionClassifier(IntentClassifierService):
    def __init__(self, llm : LLMInterface = GEMMA()):
        self.llm = llm
        self.intent_prompt = """
Analiza el contexto de conversacion y el siguiente mensaje del usuario y clasifícalo **estrictamente en UNA** de las siguientes intenciones.  
Intención anterior: {last_intention}
---  
1. `info_beca`: el usuario menciona explícitamente el nombre o identificador de una beca (propio o inferido), pide plazos, requisitos, enlaces o información detallada sobre esa beca en particular.  
   - **Ejemplos**:  
     - “¿Qué sabes de beca_mec_general?”  
     - “Info sobre Beca Santander”  
     - “Cuéntame más sobre la beca Fulbright”  
     - “¿Cuándo abre la convocatoria de la MEC?”  
     - “¿Qué requisitos tiene la Erasmus Mundus?”  
     - “Dame el enlace de la beca UPV Deporte”  

2. `explicar_termino`: pide la definición o aclaración de un término, categoría o forma de financiación relacionada con becas.  
   - **Ejemplos**:  
     - “¿Qué es mérito académico?”  
     - “Explícame qué son las becas completas”  
     - “¿Qué significa ‘convocatoria abierta’?”  


3. `buscar_por_criterio`: el usuario inicia o continúa una búsqueda guiada de becas, expresa necesidades genéricas sobre becas **o** emplea comandos de flujo para **modificar** o **omitir** criterios de búsqueda.
   - **Ejemplos de búsqueda guiada**:  
     - “necesito una beca para mi grado”  
     - “¿qué becas hay para estudiar en Francia?”  
     - “recomiéndame becas para un doctorado internacional”  
     - “para ingeniería”  


4. `general_qa`: consultas amplias o consejos sobre el proceso de solicitud, documentación o funcionamiento general, sin intención inmediata de buscar becas ni de explicación de un término específico.  
   - **Ejemplos**:  
     - “¿Qué documentos suelen pedir?”  
     - “¿Cómo es el proceso en general?”  



**Instrucciones de salida:**
Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la estructura: `{{ "intention": "..." }}`.



Contexto Previo de la conversación:
\"\"\"{context}\"\"\"

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
          
          
    def classify_intention(self, message: str, context: str = None, last_intention: str = None) -> dict:
        """
        Clasificación principal. Ahora puede tomar contexto del flujo guiado.
        """
        prompt = self.intent_prompt.format(message=message, context=context, last_intention=last_intention)
        resp = self.llm.generate(prompt)
        intent_data = self._extract_json(resp) # Obtener el dict completo
        intent = intent_data.get("intention") if isinstance(intent_data, dict) else None
        
        valid_intents = {"buscar_por_criterio", "info_beca", "explicar_termino", "general_qa"}
        if intent not in valid_intents:
            logger.warning(f"Intent classification failed or returned invalid intent. Raw LLM resp: '{resp}'. Extracted: '{intent_data}'. Falling back to general_qa.")
            intent = "general_qa" # Fallback

        return {"intention": intent , "navigation": None}




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