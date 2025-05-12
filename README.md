# Chatbot de Búsqueda de Becas

Un asistente conversacional en lenguaje natural para guiar a estudiantes en la búsqueda de becas, apoyado por un modelo LLM local (LLAMA 3.2) y un motor lógico Prolog.

---

## 🏆 Características

- Búsqueda por **código de beca** o por **criterios** (área, financiación, lugar…).  
- Explicaciones de criterios bajo demanda.  
- Edición de filtros en cualquier momento.  
- Flujo guiado 100 % en lenguaje natural (sin botones).  
- Arquitectura modular con **Clean Architecture** y **Chain of Responsibility**.

---

## 📐 Arquitectura general

1. **Domain**: entidades (`Scholarship`, `FilterCriteria`) y **interfaces** (`ScholarshipRepository`, `IntentClassifierService`).  
2. **Application**: casos de uso (`SearchByCode`, `FilterScholarship`, `ExplainCriterion`, etc.) y pipeline de handlers (`PreprocessHandler`, `IntentHandler`, `FlowHandler`, `GenerationHandler`).  
3. **Infrastructure**: adaptadores concretos para Prolog (`PrologScholarshipRepository`) y LLM (`LLAMAInterface` o stub).  
4. **Presentation**: API REST/WebSocket con FastAPI.

---

## 🚀 Primeros pasos

### Requisitos previos

- Python 3.10+  
- Git  
- (Opcional) Docker  

### Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/chatbot-becas.git
cd chatbot-becas

# Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```  

### Variables de entorno

Crea un archivo `.env` con las rutas a tu modelo y KB de Prolog:

```env
LLAMA_PATH=./models/llama-3.2
PROLOG_KB=./becas.pl
```  

### Ejecutar el servidor

```bash
uvicorn src.presentation.api:app --reload
```  
API disponible en `http://127.0.0.1:8000`.

---

## 🗂️ Estructura del proyecto

```text
project-root/
├── config/                # flujos, mapeos y glosario en JSON
│   ├── flow_config.json
│   ├── mappings.json
│   └── glossary.json
├── docs/                  # documentación viva: visión, flujos, personas
├── src/
│   ├── domain/            # entidades e interfaces puras
│   ├── application/       # casos de uso y pipeline de handlers
│   │   ├── services/
│   │   └── pipeline/
│   ├── infrastructure/    # adaptadores (Prolog, LLM, repositorios JSON)
│   └── presentation/      # FastAPI (endpoints REST/WebSocket)
├── tests/                 # tests unitarios e integración
├── main.py                # punto de entrada opcional
├── README.md
└── Dockerfile
```  

---

## ✅ Testing

```bash
# Ejecutar tests unitarios e integración
pytest --maxfail=1 --disable-warnings -q
```  

---

## 🛣️ Roadmap

1. **Sprint 1**: stubs e infraestructura mínima + pipeline de juguete + endpoint `/chat`.  
2. **Sprint 2**: implementar PrologConnector y SearchByCode completos.  
3. **Sprint 3**: extracción de criterios y FilterScholarship.  
4. **Sprint 4**: explicaciones de criterios y editar filtros.  
5. **Sprint 5**: pruebas de usuario y optimización de prompts de LLAMA.

---

## 🤝 Contribuir

1. Haz un _fork_  
2. Crea una _branch_ feature: `git checkout -b feature/tu-idea`  
3. Realiza tus cambios y _commitea_  
4. Abre un _pull request_  

---

## 📄 Licencia

[MIT](LICENSE)
