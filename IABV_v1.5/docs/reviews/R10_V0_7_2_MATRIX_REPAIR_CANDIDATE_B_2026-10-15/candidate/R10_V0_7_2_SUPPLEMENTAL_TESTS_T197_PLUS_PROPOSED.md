# R10 v0.7.2 — Pruebas suplementarias T197+ (PROPUESTAS, no normativas)

**Estado:** `PROPOSED`, fuera del registro normativo T123–T196. No asigna ni reasigna IDs en el CSV. Su incorporación como normas requiere revisión y autoridad normativa separadas. Los resultados negativos no usan códigos no definidos.

| ID propuesto | Fixture determinista | Oráculo esperado | Base / límite |
|---|---|---|---|
| T197 | `QUARANTINE_RELEASED` tras resolución independiente, sin rederivar elegibilidad ni crear evaluación/contribución nuevas. | La liberación no activa nada; la barrera/proyección queda sin adopción hasta la derivación explícita y CAS. | §12: liberación no activa directamente; §8.3 exige nueva evaluación/contribución al restaurar. |
| T198 | Antes de adoptar la nueva evaluación restaurada, el digest usado por validación difiere del bundle congelado. | `CRITERIA_MISMATCH`; sin evaluación válida/adopción/efectos; plan no se publica. | §5. |
| T199 | Después de revisar elegibilidad, `AUTHORIZATION_REVOKED` incrementa generación antes de commit. | `AUTHORIZATION_GENERATION_MISMATCH`; plan `VOIDED`; contribución invisible; delta 0. | §9. |
| T200 | Otro escritor cambia `projection_generation` después de leer el valor esperado y antes del CAS. | CAS no adopta el candidato; puntero/generación no cambian por el escritor perdedor y no hay publicación parcial. El contrato no nombra un código específico de CAS fallido. | §6.3 y §8.2. |
| T201 | Reemplazo de C_PREV por C_NEXT con lecturas concurrentes en ambos lados del commit. | Cada snapshot ve C_PREV solo antes o C_NEXT solo después; nunca ambos. | §§1.3, 8.1–8.2. |
| T202 | Interrupción con plan `PARTIAL`, antes de confirmar publicación; luego recuperación con guardas fijas inválidas. | Las contribuciones preparadas siguen invisibles; recuperación marca el plan `VOIDED`; ningún efecto parcial es visible. | §§8.1–8.2. |
| T203 | El captor proporciona `in_reply_to_turn_id`, pero la plataforma no lo atesta. | `UNCORRELATED`; no `result_id` automático ni efecto. | §§4.1–4.2. |
| T204 | Respuesta con `destination_session_id` distinto al despacho autenticado, aunque turno/nonce parezcan coincidir. | `UNCORRELATED`; no se ocupa el slot AUTO ni se evalúa. | §4.1. |
| T205 | El actor que produjo o evaluó el conflicto intenta emitir `CONFLICT_RESOLVED`. | El actor no satisface la independencia; el conflicto continúa bloqueado y ninguna contribución se hace visible. No se inventa código de error. | §§6.2, 11. |
| T206 | Una captura llega después de un supuesto vencimiento de nonce, con nonce coincidente y vínculo de turno válido. | **Sin oráculo normativo actual**: el contrato no define TTL/expiry del nonce. La prueba requiere una regla autorizada antes de fijar aceptación o `UNCORRELATED`. | §4.1 requiere coincidencia nonce; §2.3/§10 definen reloj/deadline, pero no vencimiento de nonce. |
| T207 | Repetir un `ATTACHED` manual con el mismo attachment_id/digest y luego mismo ID con digest diferente. | **Sin oráculo normativo actual** para deduplicación/conflicto manual. Debe resolverse antes de exigir idempotencia manual; el aislamiento MANUAL/AUTO sí es exigible. | §§2.2 y 4.2 limitan deduplicación explícita a eventos automáticos. |

