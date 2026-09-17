# 🚦 Semáforo Inteligente

Protótipo de semáforo adaptativo com IA aplicada a duas funcionalidades:

1. **Fluxo de trânsito adaptativo** — detecta veículos parados na via (via
   câmera/webcam) e ajusta dinamicamente o tempo de verde conforme o volume
   de veículos parados.
2. **Prioridade a veículos de emergência** — identifica a presença de um
   veículo de emergência (polícia, bombeiros, ambulância) combinando:
   - **Visão computacional**: padrão de piscar do giroflex (vermelho/azul).
   - **Áudio**: assinatura espectral típica de sirene captada por microfone.
   - Quando detectado, o semáforo prioriza abertura do verde e um atuador
     (farol/baliza, ou GPIO real em Raspberry Pi) é acionado automaticamente.

Inclui um **dashboard web ao vivo** para acompanhar tudo isso, com stream de
vídeo, indicadores do semáforo, contadores de tráfego e alerta de emergência
— pronto para testes reais com webcam/câmera IP e, futuramente, sensores.

> ⚠️ Este é um protótipo funcional para validação de conceito. A detecção de
> veículos usa subtração de fundo (sem depender de modelos pesados), e a
> classificação de "veículo de emergência" é heurística (cor + áudio). Para
> produção, recomenda-se treinar/usar um modelo supervisionado (ex.: YOLOv8
> fine-tuned) — o código já está preparado para isso (`USE_YOLO` em
> `app/vehicle_detector.py`).

## Estrutura do projeto

```
semaforo-inteligente/
├── app/
│   ├── server.py             # Flask + SocketIO, rotas e loop de processamento
│   ├── camera_stream.py       # captura de webcam / vídeo / RTSP
│   ├── vehicle_detector.py    # detecção e contagem de veículos parados
│   ├── emergency_detector.py  # detecção de giroflex (visão) + sirene (áudio)
│   ├── traffic_controller.py  # máquina de estados do semáforo
│   └── actuators.py           # farol/baliza + GPIO (real ou simulado)
├── templates/index.html        # dashboard
├── static/css/style.css
├── static/js/app.js
├── requirements.txt
└── run.py                       # ponto de entrada
```

## Instalação

```powershell
cd semaforo-inteligente
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se `sounddevice` falhar na instalação (algumas máquinas exigem drivers de
> áudio), o sistema continua funcionando normalmente — a detecção de sirene
> fica desabilitada e apenas o giroflex (visual) é usado.

## Como executar

```powershell
python run.py
```

Parâmetros opcionais:

```powershell
python run.py --port 5000 --source 0
```

- `--source 0` → usa a webcam padrão do computador (índice 0).
- `--source 1` → segunda webcam conectada.
- `--source "C:\videos\transito.mp4"` → arquivo de vídeo local (útil para
  testar sem câmera).
- `--source "rtsp://usuario:senha@ip:porta/stream"` → câmera IP real.

Você também pode trocar a fonte **em tempo real, sem reiniciar**, pelo campo
"Fonte de vídeo" no próprio dashboard.

## Acessando a interface

Depois de iniciar o servidor, acesse no navegador:

```
http://localhost:5000
```

Ou, para acessar de outro dispositivo na mesma rede (ex.: celular apontando
para uma câmera, ou notebook em outra sala):

```
http://<IP-do-computador>:5000
```

(descubra o IP com `ipconfig` no Windows — procure "Endereço IPv4").

## Testando com sensores/câmera real

- **Webcam USB**: conecte e use `--source 0` (ou o índice correspondente).
- **Câmera IP/RTSP**: informe a URL RTSP no campo de fonte do dashboard.
- **Microfone** (detecção de sirene): marque "Ativar microfone (detecção de
  sirene)" no dashboard. Requer `sounddevice` instalado e permissão de
  microfone no sistema operacional.
- **Hardware real (Raspberry Pi)**: instale `RPi.GPIO` no dispositivo; o
  módulo `app/actuators.py` detecta automaticamente e passa a acionar pinos
  GPIO reais (farol/baliza no pino 17, luz verde no 27, luz vermelha no 22)
  em vez de apenas logar no console.

## Lógica do semáforo (resumo)

- Verde mínimo: 10s | Verde máximo: 45s | Vermelho mínimo: 8s.
- Cada veículo parado na fila estende o verde em +2.5s (até o máximo).
- Emergência detectada → abre/mantém o verde imediatamente e liga o
  farol/baliza automaticamente, voltando ao ciclo normal quando a emergência
  deixa de ser detectada.

## Próximos passos sugeridos (para evoluir o protótipo)

- Treinar um classificador supervisionado de veículos de emergência (imagens
  rotuladas de viaturas policiais, ambulâncias e bombeiros).
- Integrar sensores de indução/laço magnético para contagem física de
  veículos, complementando a câmera.
- Persistir histórico de tráfego (banco de dados) para relatórios/analytics.
- Suporte a múltiplas câmeras (um cruzamento com várias vias simultâneas).
