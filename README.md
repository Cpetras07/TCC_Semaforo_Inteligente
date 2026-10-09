# 🚦 Semáforo Inteligente

## 📌 Sobre o projeto

O **Semáforo Inteligente** é um projeto acadêmico desenvolvido como Trabalho de Conclusão de Curso (TCC), com o objetivo de criar um protótipo de semáforo adaptativo capaz de utilizar visão computacional e Inteligência Artificial para auxiliar no controle do trânsito.

O sistema busca analisar o fluxo de veículos em tempo real e adaptar o funcionamento do semáforo de acordo com as condições da via. Além disso, o projeto prevê a identificação de veículos de emergência para permitir sua passagem prioritária.

## 🎯 Objetivo

Desenvolver uma solução de semaforização inteligente capaz de tornar o controle do trânsito mais eficiente, utilizando câmeras, processamento de imagens e outros recursos computacionais para tomar decisões de forma automática.

O projeto possui dois focos principais:

- Otimizar o tempo dos sinais de acordo com o fluxo de veículos;
- Priorizar a passagem de veículos de emergência.

## ⚙️ Principais funcionalidades

### 🚗 Controle adaptativo do trânsito

O sistema utiliza uma câmera ou webcam para identificar veículos na via e analisar o fluxo de trânsito.

A partir dessas informações, o tempo de abertura do sinal verde pode ser ajustado dinamicamente de acordo com a quantidade de veículos detectados.

### 🚑 Prioridade para veículos de emergência

O sistema busca identificar veículos como:

- Ambulâncias;
- Viaturas policiais;
- Veículos do Corpo de Bombeiros.

A identificação pode combinar diferentes informações:

**Visão computacional:** análise do padrão luminoso do giroflex, principalmente luzes vermelhas e azuis.

**Áudio:** identificação de características sonoras relacionadas às sirenes por meio de um microfone.

Quando uma situação de emergência é identificada, o sistema pode priorizar a abertura do sinal verde para facilitar a passagem do veículo.

## 📊 Dashboard

O projeto também conta com um **dashboard web** para acompanhamento do funcionamento do sistema.

Por meio dele é possível visualizar informações como:

- Stream de vídeo da câmera;
- Estado atual do semáforo;
- Contagem de veículos;
- Informações sobre o fluxo de trânsito;
- Alertas relacionados à identificação de veículos de emergência.

## 🛠️ Tecnologias utilizadas

O projeto utiliza ou está sendo desenvolvido com tecnologias como:

- Python
- Visão Computacional
- Inteligência Artificial
- HTML
- CSS
- JavaScript
- ESP32
- Câmera/Webcam
- Git e GitHub

> Algumas tecnologias e funcionalidades ainda estão em desenvolvimento e podem sofrer alterações durante a evolução do projeto.

## ▶️ Como executar

> Esta seção será atualizada conforme o desenvolvimento do projeto for concluído.

Para executar o sistema será necessário possuir o ambiente Python configurado e instalar as dependências utilizadas pelo projeto.

As instruções completas de instalação, configuração e execução serão adicionadas conforme o protótipo evoluir.

## 📷 Demonstração

Imagens e capturas de tela do dashboard e do protótipo serão adicionadas nesta seção durante o desenvolvimento do projeto.

## 🚧 Status do projeto

🟡 **Em desenvolvimento**

O projeto está sendo desenvolvido como Trabalho de Conclusão de Curso e novas funcionalidades estão sendo implementadas e testadas.

## 👨‍💻 Autor

**Cauã Petras Malosti**

Estudante de Ciência da Computação.

[LinkedIn](https://www.linkedin.com/in/cau%C3%A3-petras-malosti-73a00a258/)
