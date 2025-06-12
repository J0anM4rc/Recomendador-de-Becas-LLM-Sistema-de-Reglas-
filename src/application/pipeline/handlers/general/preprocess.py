import re
import logging
from ..protocols import IHandler
from application.pipeline.context import HandlerContext

class PreprocessHandler(IHandler):
    """
    Normaliza el texto (minúsculas, sin caracteres extraños, 
    elimina espacios redundantes) y lo anota en ctx.history.
    Luego delega al siguiente handler en la pipeline.
    """
    def __init__(self, next_handler: IHandler = None):
        self.next = next_handler

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        logger = logging.getLogger("preprocess_handler")
        
        # 1. Normalizar a minúsculas
        text = ctx.raw_text.lower()

        # 2. Quitar espacios redundantes
        text = re.sub(r'\s+', ' ', text).strip()

        # 3. Eliminar caracteres no deseados (solo dejamos letras, números y signos básicos)
        text = re.sub(r'[^a-z0-9áéíóúüñ¿¡?,.?\s]', '', text)

        # 4. Guardar texto normalizado
        ctx.normalized_text = text
        
        # 5. Añadir al historial
        
        logger.debug(f"Texto normalizado: {ctx.normalized_text}")
        logger.debug(f"Historia actualizada: {ctx.history}")
        # 5. Pasar al siguiente handler
        if self.next:
            return self.next.handle(ctx)
        return ctx