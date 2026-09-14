"""Contratos públicos e autodescritivos das ferramentas MCP."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


BrazilianAddressInput = Annotated[
    str,
    Field(
        description=(
            "Endereço textual de um imóvel no Brasil, com pelo menos 5 e no "
            "máximo 500 caracteres após normalização dos espaços."
        ),
        examples=["Avenida Paulista, 1000, São Paulo, SP"],
    ),
]
OptionalBrazilianAddressInput = Annotated[
    str | None,
    Field(
        description=(
            "Endereço brasileiro usado para resolver a localização. Informe-o "
            "somente quando latitude e longitude não forem fornecidas."
        ),
        examples=["Avenida Paulista, 1000, São Paulo, SP"],
    ),
]
LatitudeInput = Annotated[
    float | None,
    Field(
        description=(
            "Latitude do imóvel entre -90 e 90 graus. Deve ser enviada junto "
            "com longitude e não pode ser combinada com endereco."
        ),
        examples=[-23.5614],
    ),
]
LongitudeInput = Annotated[
    float | None,
    Field(
        description=(
            "Longitude do imóvel entre -180 e 180 graus. Deve ser enviada junto "
            "com latitude e não pode ser combinada com endereco."
        ),
        examples=[-46.6559],
    ),
]
MonthlyConsumptionInput = Annotated[
    float | None,
    Field(
        description=(
            "Consumo médio mensal de eletricidade em kWh, positivo e finito. "
            "Informe este campo, valor_conta_reais ou ambos."
        ),
        examples=[520.0],
    ),
]
MonthlyBillInput = Annotated[
    float | None,
    Field(
        description=(
            "Valor mensal da conta de energia em reais, positivo e finito. "
            "Com consumo, define a tarifa efetiva; sozinho, estima o consumo."
        ),
        examples=[494.0],
    ),
]

ExecutionMode = Literal["google_apis", "demonstracao_offline"]
TariffSource = Literal[
    "tarifa_efetiva_da_conta",
    "tarifa_padrao_configurada",
    "tarifa_padrao_para_converter_conta",
]
ProductionSource = Literal[
    "configuracao_google_ajustada_para_potencia_e_desempenho",
    "estimativa_padrao_configurada",
    "dados_ficticios_modo_demonstracao",
]
RoofCapacityMethod = Literal[
    "contagem_google_ajustada_conservadoramente_por_area",
    "contagem_google_sem_dimensoes_referencia",
    "dados_ficticios_modo_demonstracao",
]


class PublicApiModel(BaseModel):
    """Base estrita para detectar alterações acidentais no contrato público."""

    model_config = ConfigDict(extra="forbid")


class LocationResponse(PublicApiModel):
    """Coordenadas usadas para consultar e calcular o potencial solar."""

    latitude: float = Field(
        description="Latitude final do imóvel em graus, entre -90 e 90.",
        ge=-90,
        le=90,
    )
    longitude: float = Field(
        description="Longitude final do imóvel em graus, entre -180 e 180.",
        ge=-180,
        le=180,
    )


class ToolErrorDetails(PublicApiModel):
    """Detalhes seguros de uma falha tratada pela ferramenta."""

    codigo: str = Field(
        description=(
            "Código estável e legível por máquina, como entrada_invalida, "
            "configuracao_invalida, timeout ou http_error."
        )
    )
    mensagem: str = Field(
        description="Explicação segura da falha para a IA ou para o usuário."
    )
    servico: str | None = Field(
        default=None,
        description="Serviço externo que falhou; presente apenas em erros externos.",
        exclude_if=lambda value: value is None,
    )
    status_code: int | None = Field(
        default=None,
        description="Status HTTP recebido do serviço externo, quando disponível.",
        ge=100,
        le=599,
        exclude_if=lambda value: value is None,
    )


class ToolErrorResponse(PublicApiModel):
    """Resposta de domínio malsucedida, transportada normalmente pelo MCP."""

    sucesso: Literal[False] = Field(
        description="Sempre false quando a operação não pôde ser concluída."
    )
    modo_execucao: ExecutionMode = Field(
        description="Origem da execução: APIs Google reais ou demonstração offline."
    )
    aviso_demonstracao: str | None = Field(
        default=None,
        description=(
            "Aviso de que nenhuma API externa foi consultada; existe apenas no "
            "modo demonstracao_offline."
        ),
        exclude_if=lambda value: value is None,
    )
    erro: ToolErrorDetails = Field(
        description="Código, mensagem e contexto seguro da falha tratada."
    )


class GeocodingSuccessResponse(PublicApiModel):
    """Resultado bem-sucedido da geocodificação de um endereço brasileiro."""

    sucesso: Literal[True] = Field(
        description="Sempre true quando o endereço foi convertido com sucesso."
    )
    modo_execucao: ExecutionMode = Field(
        description="Origem da execução: API Google real ou demonstração offline."
    )
    aviso_demonstracao: str | None = Field(
        default=None,
        description=(
            "Aviso de coordenadas fictícias; existe apenas no modo "
            "demonstracao_offline."
        ),
        exclude_if=lambda value: value is None,
    )
    endereco_formatado: str = Field(
        description=(
            "Endereço brasileiro padronizado pelo provedor de geocodificação; "
            "no demo, identifica explicitamente as coordenadas fictícias."
        )
    )
    latitude: float = Field(
        description="Latitude resolvida em graus, entre -90 e 90.",
        ge=-90,
        le=90,
    )
    longitude: float = Field(
        description="Longitude resolvida em graus, entre -180 e 180.",
        ge=-180,
        le=180,
    )


class SolarCalculationSuccessResponse(PublicApiModel):
    """Dimensionamento solar e estimativa financeira concluídos com sucesso."""

    sucesso: Literal[True] = Field(
        description="Sempre true quando o dimensionamento foi concluído."
    )
    modo_execucao: ExecutionMode = Field(
        description="Origem da execução: APIs Google reais ou demonstração offline."
    )
    aviso_demonstracao: str | None = Field(
        default=None,
        description=(
            "Aviso de que localização, telhado e produção são fictícios; existe "
            "apenas no modo demonstracao_offline."
        ),
        exclude_if=lambda value: value is None,
    )
    localizacao: LocationResponse = Field(
        description="Coordenadas finais usadas na consulta solar e nos cálculos."
    )
    consumo_mensal_kwh: float = Field(
        description="Consumo mensal informado ou estimado, em kWh.",
        gt=0,
    )
    valor_conta_informado_reais: float | None = Field(
        description=(
            "Valor mensal da conta informado pelo usuário, em reais; null quando "
            "somente o consumo foi fornecido."
        ),
        gt=0,
    )
    tarifa_aplicada_reais_kwh: float = Field(
        description="Tarifa usada nos cálculos, em reais por kWh.",
        gt=0,
    )
    fonte_tarifa: TariffSource = Field(
        description=(
            "Explica se a tarifa veio da razão conta/consumo, da configuração "
            "padrão ou foi usada para estimar o consumo a partir da conta."
        )
    )
    painel_referencia: str = Field(
        description="Fabricante e modelo do módulo fotovoltaico usado na estimativa."
    )
    potencia_painel_w: float = Field(
        description="Potência nominal de cada painel proposto, em watts.",
        gt=0,
    )
    largura_painel_m: float = Field(
        description="Largura do painel proposto, em metros.",
        gt=0,
    )
    altura_painel_m: float = Field(
        description="Altura do painel proposto, em metros.",
        gt=0,
    )
    preco_referencia_modulo_reais: float = Field(
        description="Preço de referência de um módulo, em reais.",
        gt=0,
    )
    mao_de_obra_instalacao_por_painel_reais: float = Field(
        description="Mão de obra estimada para instalar cada painel, em reais.",
        gt=0,
    )
    outros_custos_sistema_por_painel_reais: float = Field(
        description=(
            "Rateio por painel de inversor, estrutura, proteções, projeto e "
            "demais componentes e serviços, em reais."
        ),
        gt=0,
    )
    fator_desempenho_sistema: float = Field(
        description=(
            "Fração da energia DC considerada útil após perdas de conversão, "
            "temperatura, cabos e operação; 0.85 significa 85%."
        ),
        gt=0,
        le=1,
    )
    produtividade_mensal_por_painel_kwh: float = Field(
        description="Geração útil mensal estimada por painel, em kWh.",
        gt=0,
    )
    fonte_produtividade: ProductionSource = Field(
        description=(
            "Origem da produtividade: configuração da Solar API ajustada, "
            "fallback configurado ou dados fictícios do demo."
        )
    )
    configuracao_google_paineis: int | None = Field(
        description=(
            "Quantidade de painéis na configuração da Google Solar API "
            "selecionada; null no fallback e no demo."
        ),
        ge=1,
    )
    potencia_painel_referencia_google_w: float | None = Field(
        description=(
            "Potência, em watts, do painel de referência usado pela Google Solar "
            "API para estimar energia; null no fallback e no demo."
        ),
        gt=0,
    )
    horas_sol_maximas_ano: float | None = Field(
        description=(
            "Máximo anual de horas de sol informado pela Solar API; campo "
            "informativo que não entra diretamente na fórmula financeira."
        ),
        gt=0,
    )
    paineis_recomendados: int = Field(
        description=(
            "Quantidade de painéis proposta para atender a demanda sem ultrapassar "
            "o limite físico estimado do telhado."
        ),
        ge=1,
    )
    capacidade_google_paineis_referencia: int | None = Field(
        description=(
            "Quantidade máxima original estimada pela Google para os painéis de "
            "referência dela, antes do ajuste conservador por área; null no demo."
        ),
        ge=1,
    )
    metodo_capacidade_telhado: RoofCapacityMethod = Field(
        description=(
            "Método usado para interpretar a capacidade do telhado: ajuste por "
            "área, contagem sem dimensões ou cenário fictício do demo."
        )
    )
    limitado_pelo_telhado: bool = Field(
        description=(
            "True quando o espaço estimado do telhado impede a geração de "
            "compensar todo o consumo informado."
        )
    )
    geracao_mensal_estimada_kwh: float = Field(
        description="Geração útil total estimada do sistema por mês, em kWh.",
        gt=0,
    )
    consumo_mensal_compensado_kwh: float = Field(
        description=(
            "Parcela mensal do consumo coberta pela geração estimada, em kWh; "
            "nunca excede o consumo informado."
        ),
        gt=0,
    )
    percentual_consumo_compensado: float = Field(
        description="Percentual do consumo mensal coberto pela geração estimada.",
        gt=0,
        le=100,
    )
    investimento_estimado_reais: float = Field(
        description=(
            "Investimento inicial estimado, em reais, somando módulos, mão de "
            "obra e demais custos para todos os painéis recomendados."
        ),
        gt=0,
    )
    economia_mensal_estimada_reais: float = Field(
        description=(
            "Economia mensal inicial estimada, em reais, limitada ao consumo "
            "que pode ser compensado."
        ),
        gt=0,
    )
    payback_estimado_anos: float | None = Field(
        description=(
            "Primeiro mês completo em que a economia acumulada recupera o "
            "investimento, convertido em anos e considerando degradação; null "
            "quando não há retorno dentro de 100 anos."
        ),
        ge=0,
    )
    observacoes: list[str] = Field(
        description=(
            "Avisos necessários para interpretar premissas, limitações, origem "
            "dos dados, custos e necessidade de avaliação profissional."
        ),
        min_length=1,
    )
    endereco_geocodificado: str | None = Field(
        default=None,
        description=(
            "Endereço padronizado usado no cálculo; presente somente quando a "
            "entrada foi fornecida por endereco."
        ),
        exclude_if=lambda value: value is None,
    )


GeocodingPayload = Annotated[
    GeocodingSuccessResponse | ToolErrorResponse,
    Field(discriminator="sucesso"),
]
SolarCalculationPayload = Annotated[
    SolarCalculationSuccessResponse | ToolErrorResponse,
    Field(discriminator="sucesso"),
]


def _remove_boolean_discriminator_mapping(schema: dict[str, object]) -> None:
    """Remove mapping incompatível entre booleanos Python e JSON."""

    discriminator = schema.get("discriminator")
    if isinstance(discriminator, dict):
        discriminator.pop("mapping", None)


class GeocodingToolResponse(RootModel[GeocodingPayload]):
    """Resposta de sucesso ou erro da ferramenta de geocodificação."""

    model_config = ConfigDict(
        json_schema_extra=_remove_boolean_discriminator_mapping
    )


class SolarCalculationToolResponse(RootModel[SolarCalculationPayload]):
    """Resposta de sucesso ou erro da ferramenta de cálculo solar."""

    model_config = ConfigDict(
        json_schema_extra=_remove_boolean_discriminator_mapping
    )
