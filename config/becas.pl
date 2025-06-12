%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% BASE DE CONOCIMIENTO DE BECAS v3.4
% - 5 becas (MEC, UPV Deporte, FP Valencia, Erasmus, GV Transporte)
% - Criterios: Organismo convocante, Área de estudios, Financiamiento, Nivel educativo, Ubicación
% - Añadido tipo 'otros' en Financiamiento y Nivel educativo
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

:- encoding(utf8).
:- dynamic beca/1,
           organismo/2,
           campo_estudio/2,
           financiamiento/2,
           nivel/2,
           ubicacion/2,
           info/2,
           plazo/3,
           requisito/3,
           web_oficial/2.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 1. DECLARACIÓN DE BECAS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
beca(beca_mec_general).
beca(beca_upv_deporte).
beca(beca_fp_valencia).
beca(beca_erasmus_master).
beca(beca_gv_transporte).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 2. CRITERIOS DE CLASIFICACIÓN
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% 2.1 Organismo convocante
% - publico_estatal: Ministerio, Gobierno central
% - publico_local: Comunidad autónoma, Universidad pública
% - privado: Empresas, Fundaciones privadas
% - internacional: Instituciones extranjeras o europeas
% - otros: ONG pequeñas, entes mixtos, etc.
organismo(beca_mec_general, publico_estatal).
organismo(beca_upv_deporte, publico_local).
organismo(beca_fp_valencia, publico_local).
organismo(beca_erasmus_master, internacional).
organismo(beca_gv_transporte, publico_local).

% 2.2 Área de estudios
% - ciencias_tecnicas: Ingeniería, Tecnología, Informática
% - ciencias_sociales: Derecho, Economía, Educación, FP
% - arte_humanidades: Historia, Arte, Humanidades
% - salud: Medicina, Enfermería, Psicología
% - otros: Becas generales o multidisciplinares
campo_estudio(beca_mec_general, ciencias_sociales).
campo_estudio(beca_upv_deporte, ciencias_tecnicas).
campo_estudio(beca_fp_valencia, ciencias_sociales).
campo_estudio(beca_erasmus_master, otros).
campo_estudio(beca_gv_transporte, otros).

% 2.3 Tipo de financiamiento
% - completa: Cubre matrícula, alojamiento, manutención y transporte
% - parcial: Cubre solo una parte (ej. matrícula o importe mensual)
% - ayuda_transporte: Apoyo para gastos de desplazamiento
% - otros: Otros tipos de ayuda no previstos expresamente
financiamiento(beca_mec_general, completa).
financiamiento(beca_upv_deporte, parcial).
financiamiento(beca_fp_valencia, parcial).
financiamiento(beca_erasmus_master, completa).
financiamiento(beca_gv_transporte, ayuda_transporte).

% 2.4 Nivel educativo
% - postobligatoria_no_uni: Bachillerato, Formación Profesional
% - grado: Estudios universitarios de Grado
% - posgrado: Máster y Doctorado
% - otros: Otros niveles o modalidades no clasificados
nivel(beca_mec_general, grado).
nivel(beca_mec_general, posgrado).
nivel(beca_upv_deporte, grado).
nivel(beca_fp_valencia, postobligatoria_no_uni).
nivel(beca_erasmus_master, posgrado).
nivel(beca_gv_transporte, grado).
nivel(beca_invent, otro).

% 2.5 Ubicación geográfica
ubicacion(beca_mec_general, españa).
ubicacion(beca_upv_deporte, valencia).
ubicacion(beca_fp_valencia, valencia).
ubicacion(beca_erasmus_master, europa).
ubicacion(beca_gv_transporte, valencia).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 3. DESCRIPCIÓN DE LAS BECAS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
info(beca_mec_general, 'Beca del Ministerio de Educación de España para estudios universitarios de grado y máster, con criterios académicos y económicos.').
info(beca_upv_deporte, 'Beca para estudiantes deportistas de alto nivel en la Universitat Politècnica de València.').
info(beca_fp_valencia, 'Beca de apoyo económico para estudiantes de Formación Profesional de Grado Medio o Superior en la Comunidad Valenciana.').
info(beca_erasmus_master, 'Beca europea para cursar másteres conjuntos internacionales con alta calidad académica.').
info(beca_gv_transporte, 'Ayuda económica para estudiantes con residencia familiar alejada del campus en la Comunidad Valenciana.').

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4. PLAZOS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
plazo(beca_mec_general, apertura, 'Agosto/Septiembre (aproximado)').
plazo(beca_mec_general, cierre, 'Octubre (aproximado)').
plazo(beca_erasmus_master, apertura, 'Octubre/Noviembre (aproximado). Varía según máster.').
plazo(beca_erasmus_master, cierre, 'Abril/Mayo (aproximado). Varía según máster.').
plazo(beca_gv_transporte, apertura, '1 de Septiembre').
plazo(beca_gv_transporte, cierre, '15 de Octubre').

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 5. REQUISITOS ESPECÍFICOS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
requisito(beca_mec_general, nota_media, 'Aprobado general (5.0), varía por rama').
requisito(beca_mec_general, nacionalidad, 'Española o UE con residencia').
requisito(beca_mec_general, otros, 'Cumplir umbrales de renta familiar').
requisito(beca_erasmus_master, idioma, 'Certificado de idioma B2/C1 según máster').
requisito(beca_erasmus_master, otros, 'No residir más de 12 meses en país del consorcio en últimos 5 años').
requisito(beca_gv_transporte, residencia_requerida, 'Empadronado en Comunidad Valenciana').

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 6. ENLACE WEB OFICIAL
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
web_oficial(beca_mec_general, 'https://www.becaseducacion.gob.es/becas-y-ayudas.html').
web_oficial(beca_erasmus_master, 'https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters').
web_oficial(beca_gv_transporte, 'https://inclusio.gva.es/es/web/universidad/ayudas-transporte').
web_oficial(beca_upv_deporte, 'https://www.upv.es/').
web_oficial(beca_fp_valencia, 'https://inclusio.gva.es/es/web/formacion-profesional/becas-fp').

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 7. CONSULTAS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Auxiliar para verificar coincidencias o aceptar variables
check_match(Input, _) :- var(Input), !.
check_match(Input, Value) :- Input == Value.

% Buscar becas permitiendo criterios opcionales
buscar_beca(OrgInput, AreaInput, FinInput, NivInput, UbiInput, Beca, Info) :-
    beca(Beca),
    ( var(OrgInput)  -> true ; organismo(Beca, OrgInput) ),
    ( var(AreaInput) -> true ; campo_estudio(Beca, AreaInput) ),
    ( var(FinInput)  -> true ; financiamiento(Beca, FinInput) ),
    ( var(NivInput)  -> true ; nivel(Beca, NivInput) ),
    ( var(UbiInput)  -> true ; ubicacion(Beca, UbiInput) ),
    info(Beca, Info).
