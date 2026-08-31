# Ruta progresiva de la sección 02

## Propósito

Esta sección construye **un único producto integrado**: un chatbot CLI configurado con variables de entorno, conectado a Groq, con manejo seguro de errores, muestreo validado, historial, métricas de sesión, costo teórico y pruebas offline.

Las guías no describen nueve productos independientes ni proyectan el estado final hacia atrás. Cada una parte del resultado de la anterior, introduce un cambio acotado y deja el repositorio preparado para el siguiente paso.

## Cómo recorrer la sección

1. Comience por 02-02 y complete su checklist.
2. Continúe únicamente cuando las verificaciones de esa etapa estén verdes.
3. Aplique el delta de la siguiente guía sobre el mismo código.
4. No copie el producto final de 02-10 dentro de una etapa anterior.
5. Use los conteos como checkpoints de la ruta didáctica; el árbol final contiene todos los casos acumulados.

## Mapa de construcción

| Etapa | Incremento principal | Tests acumulados al cerrar la etapa |
| --- | --- | ---: |
| [02-02](./02-02-project-scaffold.md) | Proyecto `uv`, src-layout y herramientas de calidad | 1 |
| [02-03](./02-03-groq-account-api-key.md) | Cuenta, API key y separación `.env`/`.env.example` | 1 |
| [02-04](./02-04-first-groq-api-call.md) | Configuración tipada y primera llamada real | 1 + smoke live manual |
| [02-05](./02-05-token-usage-and-cost-estimation.md) | Uso de tokens y costo teórico con `Decimal` | 8 |
| [02-06](./02-06-groq-api-error-handling.md) | Errores tipados y mensajes seguros | 14 |
| [02-07](./02-07-temperature-and-reproducibility.md) | `LLM_TEMPERATURE`, validación, seed y harness experimental | 46 |
| [02-08](./02-08-cli-chatbot-conversation-history.md) | Dominio `ChatBot` e historial transaccional | 51 |
| [02-09](./02-09-cli-chatbot-session-usage-and-cost.md) | Estadísticas y costo acumulado de sesión | 59 |
| [02-10](./02-10-cli-chatbot-loop-and-integration.md) | Bucle CLI, comandos, composición y producto final | 78 |

## Arquitectura final

```text
.env
  └── Settings
      ├── provider / model / API key
      ├── max tokens / temperature
      └── tarifas opcionales
              ↓
        composition root
              ↓
          ChatBot domain
      ├── validated sampling
      ├── transactional history
      └── immutable session stats
              ↓
          Groq client
              ↓
           CLI loop
```

`LLM_TEMPERATURE` tiene una sola ruta productiva:

```text
.env → Settings.llm_temperature → validate_temperature → ChatBot → Groq
```

El `seed` no forma parte de la configuración normal del chatbot. Se limita al harness de 02-07 porque sirve para experimentos best-effort, no para prometer determinismo en conversaciones cuyo historial cambia.

## Criterio de producto completo

La sección termina cuando:

- la configuración no contiene secretos rastreados;
- el chatbot no hardcodea modelo, temperatura, límite de tokens ni tarifas;
- todos los límites externos tienen errores seguros;
- el historial solo se confirma después de respuestas exitosas;
- estadísticas y costo se acumulan con contratos tipados;
- el CLI integra conversación, `/stats`, `/reset` y salida limpia;
- Ruff, mypy y los **78 tests** pasan sin red;
- el smoke test live se ejecuta solo cuando se decide consumir cuota.

## Siguiente paso

Comience con [02-02-project-scaffold.md](./02-02-project-scaffold.md). La sección 03 queda fuera de este recorrido.
