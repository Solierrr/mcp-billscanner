# Calculadora Solar MCP

Servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) em Python para dimensionamento preliminar de sistemas fotovoltaicos. A ferramenta cruza consumo, tarifa, produção solar estimada e limite físico do telhado para calcular painéis, geração, investimento, economia e payback.

> As estimativas são indicativas e não substituem projeto elétrico, análise de sombreamento, orçamento ou avaliação de um profissional habilitado.

## Funcionalidades

- Entrada por latitude/longitude ou endereço textual brasileiro.
- Geocodificação restrita ao Brasil pela Google Geocoding API.
- Consulta ao endpoint `buildingInsights:findClosest` da Google Solar API.
- Consumo informado diretamente ou estimado pela conta com tarifa padrão de R$ 0,95/kWh.
- Tarifa efetiva calculada quando consumo e valor da conta são enviados juntos.
- Seleção de uma configuração em `solarPanelConfigs` compatível com a demanda e o telhado.
- Energia DC da API ajustada para o JA Solar JAM72S30-550/MR de 550 W e convertida por fator de desempenho DC→AC.
- Fallback configurável de 65 kWh/mês por painel quando não há configuração energética utilizável.
- Limite do telhado ajustado conservadoramente pelas dimensões do módulo quando a API fornece dimensões de referência.
- Preço de referência do módulo separado da estimativa de custo instalado usada no investimento.
- Payback mensal com redução linear de potência de 0,55% ao ano.
- Timeout, novas tentativas para falhas temporárias e erros JSON estruturados.
- Schemas MCP de entrada e saída autodescritivos, com tipo, unidade, finalidade e condição de presença de cada campo para clientes e agentes de IA.

## Painel comercial de referência

A configuração padrão usa o **JA Solar JAM72S30-550/MR**. A [página oficial da linha JAM72S30 MR](https://www.jasolar.eu/es/productos/jam72s30-mr) informa faixa de 540–565 W, dimensões nominais de 2278 × 1134 × 30 mm, garantia de desempenho de 25 anos e redução anual de potência de 0,55%. A [oferta brasileira da Energia Total](https://www.energiatotal.com.br/painel-solar-550w-ja-solar-jam72s30-550mr) confirma o modelo de 550 W, eficiência anunciada de 21,3%, garantia de 12 anos contra defeitos e 25 anos de potência linear. Revisões comerciais podem ter pequenas diferenças dimensionais; a oferta brasileira consultada anuncia 2279 × 1133 × 35 mm.

O modelo foi escolhido porque o [comparativo brasileiro de custo-benefício da OPS Energia](https://www.opsenergia.com/blog/ranking-modulos-fotovoltaicos-melhor-custo-beneficio-brasil) o colocou em primeiro lugar e publicou preço médio indicativo de **R$ 780**. Esse valor varia com data, estoque, frete e fornecedor, mas pode permanecer como referência configurável do módulo no cálculo demonstrativo.

Para a instalação, a [referência de mão de obra da Organizzei](https://organizzei.com.br/custo-mao-de-obra-instalar-painel-solar/) apresenta uma faixa de R$ 800 a R$ 1.500 por kWp. Como cada módulo tem 0,55 kWp, a faixa equivalente é de R$ 440 a R$ 825 por painel; a configuração usa o ponto médio de **R$ 632,50 por painel**. A [estimativa residencial da Fendel](https://fendel.com.br/2025/06/06/quanto-custa-instalar-um-sistema-de-energia-solar-residencial-em-uberlandia-em-2025/) reforça que a mão de obra varia com a complexidade, e a [SolarPrime](https://solarprime.com.br/kit-energia-solar-residencial-preco/) alerta que kits avulsos normalmente não incluem instalação, projeto e homologação.

Para não cobrar a instalação duas vezes, o total padrão de R$ 1.800 por painel foi apenas decomposto: **R$ 780 do módulo + R$ 632,50 de mão de obra + R$ 387,50 de inversor, estrutura, cabeamento, proteções, projeto e outros serviços rateados**. Os três componentes entram uma única vez no investimento.

As fontes foram consultadas em 13/09/2026. Todos os valores devem ser atualizados por cotação antes de qualquer decisão. A taxa de 0,55% é um parâmetro da garantia de desempenho, não uma medição específica do imóvel nem promessa de geração. A página oficial consultada não apresenta uma taxa distinta para o primeiro ano, portanto o software não inventa essa perda adicional.

*Content was rephrased for compliance with licensing restrictions.*

## Estrutura

```text
.
├── main.py                         # entrypoint MCP stdio
├── app/
│   ├── api_models.py               # contratos públicos Pydantic e descrições MCP
│   ├── config.py                   # ambiente e hipóteses configuráveis
│   ├── contracts.py                # contrato comum dos adapters
│   ├── service.py                  # validações e cálculos puros
│   ├── mcp_server.py               # ferramentas e orquestração MCP
│   ├── demo/
│   │   ├── client.py               # dados fictícios, sem rede
│   │   └── __main__.py             # python -m app.demo
│   └── normal/
│       └── google_client.py         # Solar API e Geocoding API
├── tests/                          # testes unitários e de contrato MCP
├── examples/                       # entradas e saídas JSON copiáveis
├── pyproject.toml                  # instalação e versões fixadas
├── .env.example                    # modelo de configuração sem segredo
└── mcp.example.json                # registro portátil para o cliente MCP
```

## Pré-requisitos

- Python 3.11 a 3.14. Python 3.13 é recomendado enquanto o ecossistema conclui a compatibilidade com 3.14.
- Para o **modo offline**, não é necessário Google Cloud, cartão ou chave.
- Para o **modo real**, é necessário projeto Google Cloud com faturamento, Solar API e, opcionalmente, Geocoding API.

## Instalação no Windows

No PowerShell, dentro da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

O arquivo `.env` está no `.gitignore`. Nunca versione ou envie uma chave real para logs, mensagens ou commits. O servidor eleva os loggers `httpx` e `httpcore` para `WARNING`, pois as APIs Google recebem a chave na query string e um log informativo da URL completa poderia expô-la.

## Testar sem API, cartão ou faturamento

A demonstração é um programa separado. Ela não é habilitada pelo `.env` e não é usada por `main.py`. Execute:

```powershell
python -m app.demo
```

Nesse comando:

- nenhuma chamada HTTP é realizada;
- `GOOGLE_SOLAR_API_KEY` pode ficar vazia;
- potência, dimensões, degradação e preço de referência vêm do painel comercial documentado acima;
- potencial do telhado, produção solar e coordenadas continuam fictícios somente dentro do processo de demonstração;
- a resposta contém `"modo_execucao": "demonstracao_offline"` e um aviso explícito;
- o fluxo valida entradas, tarifa, painéis, investimento, economia e payback.

O entrypoint MCP normal é `python main.py`. Ele força o adapter `app/normal` e nunca seleciona os dados de `app/demo`, mesmo que exista uma variável local antiga chamada `DEMO_MODE`.

Entrada usada no exemplo offline:

```json
{
  "latitude": -23.5614,
  "longitude": -46.6559,
  "consumo_mensal_kwh": 520,
  "valor_conta_reais": 494
}
```

Você também pode enviar `endereco` ao demo para testar o encadeamento, mas as coordenadas retornadas continuarão simuladas. Isso testa o software, não o imóvel.

### Por que existe geocodificação?

A Solar API trabalha com **latitude e longitude**, não com endereço escrito. A geocodificação serve somente para converter algo como `"Avenida Paulista, 1000"` em coordenadas.

- Se você já envia `latitude` e `longitude`, a Geocoding API **não é chamada**.
- Se envia `endereco`, o modo real usa a Google Geocoding API antes da Solar API.
- Não existe uma segunda variável de chave: a mesma `GOOGLE_SOLAR_API_KEY` pode ser autorizada para as duas APIs.
- `GEOCODING_API_URL` no `.env` é apenas o endereço técnico do serviço, não uma credencial.

## Onde Solar API e Geocoding são usadas

### Google Solar API

1. `app/config.py` define `SOLAR_API_URL`, cujo padrão é `https://solar.googleapis.com/v1/buildingInsights:findClosest`.
2. `app/mcp_server.py`, dentro de `calcular_sistema_solar`, chama `api_client.fetch_building_insights(latitude, longitude)`.
3. No modo normal, essa chamada chega a `GoogleApiClient.fetch_building_insights` em `app/normal/google_client.py`.
4. O cliente envia latitude, longitude, qualidade requerida e chave para o endpoint e devolve `solarPotential` ao serviço de cálculo.

### Google Geocoding API

1. `app/config.py` define `GEOCODING_API_URL`, cujo padrão é `https://maps.googleapis.com/maps/api/geocode/json`.
2. Se a entrada contiver `endereco`, `_resolve_location` em `app/mcp_server.py` chama `api_client.geocode_address(endereco)`.
3. No modo normal, `GoogleApiClient.geocode_address` envia endereço, país `BR`, região, idioma e chave, então retorna latitude e longitude.
4. Com essas coordenadas resolvidas, o servidor chama a Solar API.

Se a entrada já tiver `latitude` e `longitude`, o passo de Geocoding é ignorado e somente a Solar API é chamada. `python main.py` usa sempre esses adapters reais; `python -m app.demo` não chama nenhum dos dois endpoints.

## Preparação no Google Cloud (somente modo real)

1. Crie ou selecione um projeto no Google Cloud Console.
2. Vincule uma conta de faturamento.
3. Habilite **Solar API** e, somente se aceitar endereços textuais, **Geocoding API**.
4. Crie uma chave em **APIs e serviços > Credenciais**.
5. Em restrições da API, permita Solar API e inclua Geocoding API apenas se ela for utilizada.
6. Salve a chave no `.env` local.

O código não cria projeto, faturamento ou credenciais automaticamente. Essas operações precisam ser concluídas por alguém autorizado na conta Google Cloud.

## Execução local

Execute manualmente em um terminal:

```powershell
python main.py
```

O processo usa transporte MCP `stdio`, portanto permanece aguardando um cliente MCP. Para encerrar, use `Ctrl+C`.

## Registro no Kiro ou em outro cliente MCP

No Kiro, abra a configuração MCP pela feature panel ou procure por **MCP** na Command Palette. Copie `mcp.example.json` e substitua os dois caminhos pelo local real do clone:

```json
{
  "mcpServers": {
    "calculadora-solar": {
      "command": "C:\\caminho\\absoluto\\ai-billscanner\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\caminho\\absoluto\\ai-billscanner\\main.py"
      ],
      "disabled": false
    }
  }
}
```

Não é necessário colocar a chave no JSON: `app/config.py` procura o `.env` na raiz do projeto. Se preferir definir `env` no cliente MCP, mantenha a configuração fora do Git.

## Testes unitários e de contrato

A suíte usa apenas `unittest`, incluído no Python:

```powershell
python -m unittest discover -s tests -v
```

Os **25 testes** não chamam serviços externos. Eles cobrem configuração, validações, tarifas, dimensionamento, payback, limite do telhado, adapters demo/normal, registro MCP, `main.py` e também:

- descrição de todos os parâmetros de entrada e de todas as propriedades de saída publicadas pelo FastMCP;
- união de sucesso/erro discriminada por `sucesso` e rejeição de propriedades de saída desconhecidas;
- validação e serialização exata dos exemplos JSON pelos modelos Pydantic;
- retorno de `structuredContent` sem wrapper `result`;
- omissão de contexto opcional indisponível em erros e proteção dos logs HTTP informativos.

## Exemplos de entrada e saída

Os arquivos podem ser copiados diretamente para um cliente MCP:

- `examples/calcular_sistema_solar.input.json`
- `examples/calcular_sistema_solar.output.demo.json`
- `examples/geocodificar_endereco.input.json`
- `examples/geocodificar_endereco.output.demo.json`

Os arquivos `*.output.demo.json` são exemplos executáveis e passam sem alteração pelos modelos públicos. O contrato normativo é o schema MCP gerado de `app/api_models.py`.

Entrada resumida de cálculo:

```json
{
  "latitude": -23.5614,
  "longitude": -46.6559,
  "consumo_mensal_kwh": 520,
  "valor_conta_reais": 494
}
```

Saída resumida no modo demo:

```json
{
  "sucesso": true,
  "modo_execucao": "demonstracao_offline",
  "painel_referencia": "JA Solar JAM72S30-550/MR",
  "preco_referencia_modulo_reais": 780.0,
  "mao_de_obra_instalacao_por_painel_reais": 632.5,
  "outros_custos_sistema_por_painel_reais": 387.5,
  "paineis_recomendados": 8,
  "geracao_mensal_estimada_kwh": 521.33,
  "investimento_estimado_reais": 14400.0,
  "economia_mensal_estimada_reais": 494.0,
  "payback_estimado_anos": 2.5
}
```

Consulte o arquivo `*.output.demo.json` correspondente para ver o payload completo.

## Ferramentas MCP

### `geocodificar_endereco`

Converte um endereço brasileiro em endereço padronizado, latitude e longitude. Use quando o consumidor não possuir coordenadas.

Entrada:

```json
{
  "endereco": "Avenida Paulista, 1000, São Paulo, SP"
}
```

Resposta real ilustrativa:

```json
{
  "sucesso": true,
  "modo_execucao": "google_apis",
  "endereco_formatado": "Av. Paulista, 1000 - São Paulo - SP, Brasil",
  "latitude": -23.0,
  "longitude": -46.0
}
```

As coordenadas acima são apenas ilustrativas. A ferramenta exige que o resultado da Google contenha o componente de país `BR`.

### `calcular_sistema_solar`

Dimensiona o sistema e estima investimento, economia e payback.

Com coordenadas:

```json
{
  "latitude": -23.5614,
  "longitude": -46.6559,
  "consumo_mensal_kwh": 520,
  "valor_conta_reais": 510
}
```

Com endereço e conta:

```json
{
  "endereco": "Avenida Paulista, 1000, São Paulo, SP",
  "valor_conta_reais": 510
}
```

Regras de entrada:

- Informe `latitude` e `longitude` juntas **ou** `endereco`, nunca ambos.
- Informe pelo menos `consumo_mensal_kwh` ou `valor_conta_reais`.
- Com consumo e conta, a tarifa é `valor_conta_reais / consumo_mensal_kwh`.
- Apenas com conta, o consumo é estimado pela tarifa configurada.
- Valores energéticos devem ser positivos e finitos; coordenadas precisam estar em faixas válidas.

O resultado real depende do imóvel, das configurações retornadas pela API e das variáveis de ambiente.

### Contrato MCP autodescritivo

As duas ferramentas publicam `inputSchema` e `outputSchema`. Cada propriedade possui `description`; as entradas também possuem exemplos. A saída é uma união `oneOf` discriminada por `sucesso`: `true` seleciona o payload de sucesso e `false`, o payload de erro. Os objetos de saída têm `additionalProperties: false`, o que ajuda a detectar mudanças acidentais de contrato.

As condições entre entradas — coordenadas juntas ou endereço, além de consumo ou conta — são descritas no schema e validadas em execução. Ausências, faixas inválidas e combinações incompatíveis que chegam à ferramenta retornam o envelope estruturado com `sucesso: false`. Um valor com tipo incompatível com o `inputSchema` é rejeitado antes pelo FastMCP como erro de protocolo MCP e, por isso, não produz esse envelope.

#### Entradas

| Ferramenta | Campo | Tipo | Como usar |
|---|---|---|---|
| `geocodificar_endereco` | `endereco` | texto obrigatório | Endereço brasileiro entre 5 e 500 caracteres após normalização dos espaços. |
| `calcular_sistema_solar` | `latitude` | número ou `null`, graus | Entre -90 e 90; enviar junto com `longitude` e sem `endereco`. |
| `calcular_sistema_solar` | `longitude` | número ou `null`, graus | Entre -180 e 180; enviar junto com `latitude` e sem `endereco`. |
| `calcular_sistema_solar` | `consumo_mensal_kwh` | número ou `null`, kWh/mês | Consumo positivo; enviar este campo, a conta ou ambos. |
| `calcular_sistema_solar` | `valor_conta_reais` | número ou `null`, R$/mês | Conta positiva; com consumo define a tarifa, sozinha permite estimar o consumo. |
| `calcular_sistema_solar` | `endereco` | texto ou `null` | Alternativa brasileira às coordenadas; não combinar com latitude/longitude. |

#### Campos comuns de resposta

| Campo | Tipo | Significado |
|---|---|---|
| `sucesso` | booleano | Discriminador do envelope: `true` para resultado e `false` para erro tratado. |
| `modo_execucao` | `google_apis` ou `demonstracao_offline` | Indica se foi usado o caminho normal das APIs ou o adapter fictício sem rede. |
| `aviso_demonstracao` | texto, condicional | Existe somente no demo e informa que localização, telhado e produção são fictícios. |

#### Sucesso de `geocodificar_endereco`

| Campo | Tipo | Significado |
|---|---|---|
| `endereco_formatado` | texto | Endereço brasileiro padronizado pelo provedor; no demo identifica as coordenadas fictícias. |
| `latitude` | número, graus | Latitude resolvida entre -90 e 90. |
| `longitude` | número, graus | Longitude resolvida entre -180 e 180. |

#### Sucesso de `calcular_sistema_solar`

| Campo | Tipo/unidade | Significado |
|---|---|---|
| `localizacao` | objeto | Coordenadas finais usadas na consulta e no cálculo. |
| `localizacao.latitude` | número, graus | Latitude final entre -90 e 90. |
| `localizacao.longitude` | número, graus | Longitude final entre -180 e 180. |
| `consumo_mensal_kwh` | número, kWh/mês | Consumo informado ou estimado. |
| `valor_conta_informado_reais` | número ou `null`, R$/mês | Conta fornecida pelo usuário; `null` quando foi enviado somente consumo. |
| `tarifa_aplicada_reais_kwh` | número, R$/kWh | Tarifa efetivamente usada nos cálculos. |
| `fonte_tarifa` | enumeração | Informa se a tarifa veio da conta/consumo, da configuração padrão ou da conversão da conta. |
| `painel_referencia` | texto | Fabricante e modelo do módulo usado na estimativa. |
| `potencia_painel_w` | número, W | Potência nominal de cada painel proposto. |
| `largura_painel_m` | número, m | Largura do painel proposto. |
| `altura_painel_m` | número, m | Altura do painel proposto. |
| `preco_referencia_modulo_reais` | número, R$ | Preço de referência de um módulo. |
| `mao_de_obra_instalacao_por_painel_reais` | número, R$/painel | Mão de obra estimada para instalar cada painel. |
| `outros_custos_sistema_por_painel_reais` | número, R$/painel | Rateio de inversor, estrutura, proteções, projeto e demais itens. |
| `fator_desempenho_sistema` | número entre 0 e 1 | Fração útil após perdas; `0.85` significa 85%. |
| `produtividade_mensal_por_painel_kwh` | número, kWh/mês | Geração útil mensal estimada de cada painel. |
| `fonte_produtividade` | enumeração | Origem da produtividade: configuração Solar API ajustada, fallback ou dados fictícios. |
| `configuracao_google_paineis` | inteiro ou `null` | Painéis da configuração da Google Solar API selecionada; `null` no fallback e no demo. |
| `potencia_painel_referencia_google_w` | número ou `null`, W | Potência do painel de referência usada pela Google; `null` no fallback e no demo. |
| `horas_sol_maximas_ano` | número ou `null`, h/ano | Máximo anual informado pela Solar API; é informativo e não entra diretamente na fórmula financeira. |
| `paineis_recomendados` | inteiro | Quantidade proposta sem ultrapassar o limite físico estimado do telhado. |
| `capacidade_google_paineis_referencia` | inteiro ou `null` | Máximo original estimado pela Google para os painéis de referência dela, antes do ajuste por área; `null` no demo. |
| `metodo_capacidade_telhado` | enumeração | Método usado para interpretar a capacidade: ajuste por área, contagem sem dimensões ou demo fictício. |
| `limitado_pelo_telhado` | booleano | `true` quando o espaço estimado impede compensar todo o consumo. |
| `geracao_mensal_estimada_kwh` | número, kWh/mês | Geração útil total estimada do sistema. |
| `consumo_mensal_compensado_kwh` | número, kWh/mês | Parcela do consumo coberta pela geração; nunca excede o consumo. |
| `percentual_consumo_compensado` | número, % | Percentual do consumo coberto pela geração. |
| `investimento_estimado_reais` | número, R$ | Soma estimada de módulos, mão de obra e demais custos. |
| `economia_mensal_estimada_reais` | número, R$/mês | Economia inicial limitada ao consumo que pode ser compensado. |
| `payback_estimado_anos` | número ou `null`, anos | Momento em que a economia acumulada recupera o investimento; `null` se não ocorrer em 100 anos. |
| `observacoes` | lista de textos | Premissas, limitações, origem dos dados, custos e recomendação de avaliação profissional. |
| `endereco_geocodificado` | texto, condicional | Endereço padronizado; existe somente quando a entrada foi fornecida por `endereco`. |

Os nomes que contêm `google` indicam **proveniência**: são valores ou quantidades originalmente recebidos da Google Solar API antes dos ajustes para o painel comercial. Eles foram preservados para não quebrar o JSON existente. No demo, esses campos são `null`; `fonte_produtividade` e `metodo_capacidade_telhado` identificam explicitamente os dados fictícios.

#### Erro tratado

| Campo | Tipo | Significado |
|---|---|---|
| `erro` | objeto | Contexto seguro e legível por máquina sobre a falha. |
| `erro.codigo` | texto | Código estável, como `entrada_invalida`, `configuracao_invalida`, `timeout` ou `http_error`. |
| `erro.mensagem` | texto | Explicação segura para a IA ou para o usuário. |
| `erro.servico` | texto, condicional | Serviço que falhou; aparece somente em erros externos. |
| `erro.status_code` | inteiro, condicional | Status HTTP externo, quando disponível. |

Exemplo:

```json
{
  "sucesso": false,
  "modo_execucao": "google_apis",
  "erro": {
    "codigo": "entrada_invalida",
    "mensagem": "latitude deve estar entre -90 e 90."
  }
}
```

Campos condicionais são omitidos quando não se aplicam; não são adicionados como `null`. Em contraste, campos de domínio que fazem parte de todo sucesso de cálculo permanecem presentes e podem ser `null`: `valor_conta_informado_reais`, os campos Google, `horas_sol_maximas_ano` e `payback_estimado_anos`.

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---:|---|
| `GOOGLE_SOLAR_API_KEY` | sem padrão | Credencial obrigatória para as APIs Google |
| `SOLAR_API_URL` | endpoint Google `buildingInsights` | Endpoint HTTPS de potencial solar |
| `SOLAR_API_AUTH_MODE` | `google_api_key` | `google_api_key` para Google ou `none` para API central compatível |
| `GEOCODING_API_URL` | endpoint Google Geocoding | Deve permanecer em `maps.googleapis.com` |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Timeout finito por requisição |
| `HTTP_MAX_ATTEMPTS` | `3` | Tentativas para timeout, rede, 429, 5xx e `UNKNOWN_ERROR` |
| `DEFAULT_TARIFF_REAIS_KWH` | `0.95` | Conversão quando faltam dados para tarifa efetiva |
| `PANEL_REFERENCE` | `JA Solar JAM72S30-550/MR` | Fabricante e modelo usados como referência |
| `PANEL_POWER_WATTS` | `550` | Potência nominal do módulo de referência |
| `PANEL_WIDTH_METERS` | `1.134` | Largura nominal da linha oficial consultada |
| `PANEL_HEIGHT_METERS` | `2.278` | Altura nominal da linha oficial consultada |
| `PANEL_MODULE_REFERENCE_PRICE_REAIS` | `780` | Preço de referência do módulo incluído no investimento |
| `INSTALLATION_LABOR_COST_PER_PANEL_REAIS` | `632.50` | Mão de obra estimada por painel; equivale ao ponto médio da faixa pesquisada por kWp |
| `OTHER_SYSTEM_COST_PER_PANEL_REAIS` | `387.50` | Rateio por painel de inversor, estrutura, proteções, projeto e demais itens |
| `FALLBACK_PANEL_MONTHLY_KWH` | `65` | Produtividade usada sem configuração anual compatível |
| `SYSTEM_PERFORMANCE_RATIO` | `0.85` | Conversão da energia DC da API em geração útil estimada |
| `ANNUAL_PANEL_DEGRADATION_RATE` | `0.0055` | Redução linear anual de potência usada no payback (0,55%) |

## Critério de cálculo

1. Resolve e valida localização e demanda.
2. Obtém potencial solar, configurações e quantidade máxima de painéis no telhado.
3. Quando há dimensões de referência, reduz conservadoramente o máximo caso o módulo configurado ocupe mais área; nunca aumenta a contagem da Google apenas por área.
4. Para cada configuração que cabe no limite, ajusta `yearlyEnergyDcKwh` pela razão de potência do módulo e por `SYSTEM_PERFORMANCE_RATIO`.
5. Seleciona a menor configuração ajustada que atende à demanda; se nenhuma atender, escolhe a maior configuração compatível.
6. Sem potência de referência ou configuração compatível, usa o fallback mensal configurado.
7. Calcula economia apenas sobre o consumo que a geração útil estimada consegue compensar.
8. Calcula o investimento como `painéis recomendados × (módulo + mão de obra + outros custos rateados)`, sem duplicar nenhum componente.
9. Simula a economia mês a mês, reduzindo linearmente a potência, e considera o payback atingido no primeiro mês completo em que a economia acumulada cobre o investimento.

No mês de índice `m`, contado a partir de zero, a geração usada no payback é:

```text
geração_inicial × max(0, 1 - taxa_anual × m / 12)
```

A taxa padrão de `0.0055` representa redução linear de 0,55 ponto percentual por ano conforme a informação de garantia da linha. No começo do cálculo a retenção é 100%; após 25 anos, essa aproximação resulta em 86,25%. Quantidade de painéis, geração inicial e investimento não são aumentados por causa do desgaste; somente a economia futura usada no payback diminui.

Mesmo com o ajuste por área, o layout é aproximado: formato do telhado, corredores, obstáculos e dimensões exatas precisam de projeto. Não são modelados mau uso, quebra, instalação incorreta, sujeira anormal ou falta de manutenção. Também ficam fora do cálculo financiamento, inflação energética, custo de capital, manutenção, consumo simultâneo, regras locais de compensação e custo fixo da distribuidora.

## Evolução para API centralizada

A ferramenta MCP não conhece detalhes de HTTP. A integração real está isolada em `app/normal/google_client.py`; o modo offline fica em `app/demo/client.py`.

- Se a API central preservar parâmetros e resposta do `buildingInsights`, configure `SOLAR_API_URL=https://...` e `SOLAR_API_AUTH_MODE=none`.
- A chave Google nunca é enviada a host diferente de `solar.googleapis.com` e nenhuma API externa pode usar HTTP.
- Se a API central exigir outro contrato ou autenticação, ajuste somente o adapter preservando `fetch_building_insights` e o contrato MCP.

Assim, prompts, chatbot e consumidores MCP não precisam mudar.

## Estado de validação

Compilação, importação, parsing das configurações, 25 testes e cenários determinísticos de cálculo podem ser validados sem chave. A suíte também inspeciona os schemas publicados e executa as duas ferramentas MCP offline para confirmar que `structuredContent` preserva exatamente os exemplos JSON. Uma chamada real ponta a ponta depende de chave válida, faturamento e APIs habilitadas no Google Cloud.

## Licença

Consulte [LICENSE](LICENSE).
