# Amazon DynamoDB — Computação de Alto Desempenho

Apresentação sobre o **Amazon DynamoDB** para a disciplina de Computação de Alto Desempenho da **UEPB**.

Autor: **Vítor Raimundo Fernandes Gabínio**

## Conteúdo

| Arquivo | O que é |
| --- | --- |
| [`slides.html`](slides.html) | Slides (18), em HTML puro. Abra no navegador. |
| [`roteiro.html`](roteiro.html) | Roteiro da fala, slide a slide, com tempos e perguntas prováveis. |
| [`guia_demonstracao.html`](guia_demonstracao.html) | Passo a passo da demonstração na AWS (console + CloudShell). |
| [`demo/demo_dynamodb.py`](demo/demo_dynamodb.py) | Script Python (boto3) usado na demonstração de desempenho. |
| `img/` | Imagens usadas nos slides e no guia. |
| `video/` | Local do vídeo da demonstração (`video/demo.mp4`). |

## Como apresentar

Abra `slides.html` no navegador, com a pasta inteira junto (as imagens e o vídeo são carregados das subpastas).

- `→` / `←`, `PageDown` / `PageUp` ou passador de slides: navegar
- `F`: tela cheia
- `Espaço` no slide do vídeo: play/pause

## Demonstração

No **AWS CloudShell**, na região escolhida:

```bash
python3 demo_dynamodb.py           # cria a tabela, mede escrita, latência e Query x Scan
python3 demo_dynamodb.py --apagar  # remove a tabela
```

Detalhes, custos e limpeza em [`guia_demonstracao.html`](guia_demonstracao.html).

## Créditos das imagens

- Diagramas `HowItWorks*.png`, `dax_high_level.png` e `CreateTableMusic.png`: [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/), Amazon Web Services.
- `paper_arquitetura.png` e `paper_timeline.png`: Elhemali et al., [*Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service*](https://www.usenix.org/conference/atc22/presentation/vig), USENIX ATC 2022.
- `uepb_logo.svg`: marca da Universidade Estadual da Paraíba, via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Universidade_Estadual_da_Para%C3%ADba.svg).

As demais referências estão no slide de referências.
