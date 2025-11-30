# src/slack_service.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.log_evento import registrar_log_evento 
from utils.Database import Fazer_consulta_banco

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
LINK_PAINEL = os.getenv("LINK_PAINEL")
LINK_HOME = os.getenv("LINK_HOME")

slack_client = None


if SLACK_BOT_TOKEN:
    slack_client = WebClient(token=SLACK_BOT_TOKEN)
    print(" [SLACK SERVICE] Cliente Slack inicializado com sucesso.")
else:
    print(" [SLACK SERVICE] AVISO: Variável de ambiente SLACK_BOT_TOKEN não encontrada. O envio de alertas está desativado.")
# --------------------------------------

def procurar_informacoes_slack(idMaquina: int):
    """
    Recebe o idMaquina para identificação no banco de dados
    Retorna a o ID DO CANAL DO SLACK
    """
    IDENTIFICADOR = Fazer_consulta_banco({
        "query": """
                SELECT e.idEmpresa FROM Empresa AS e Join Maquina AS m on e.idEmpresa = m.fkEmpresa 
                WHERE m.idMaquina = %s;        
        """, 
        "params": (idMaquina, )
    })
    slackInfoRes = Fazer_consulta_banco({
        "query": """
                SELECT ID_CANAL_SLACK FROM vw_Dados_Slack WHERE IDENTIFICADOR_EMPRESA = %s;        
        """, 
        "params": (IDENTIFICADOR[0][0], )
    })

    return slackInfoRes[0][0]

def formatar_mensagem_alerta(idMaquina:int, alerta_descricao: dict, informacoes_maquina: dict,nomeMaquina:str,  informacoes_componentes:dict) -> list:
    """ 
    Array blocks para formatação
    para editar o formato acessar https://app.slack.com/block-kit-builder
    """
    print(idMaquina)
    print(alerta_descricao)
    print(informacoes_maquina)
    print(nomeMaquina)
    print(informacoes_componentes)
    blocks_container = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": alerta_descricao["titulo"]
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alerta_descricao["sub-titulo"]
                }
            },
            {
                "type": "divider"
            },
            {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Contexto Técnico:*"
                    },
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"* Nome/ID:*\n{str(nomeMaquina)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Sistema Operacional:*\n{str(informacoes_maquina['sistemaOperacional'])}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Modelo de Hardware:*\n{str(informacoes_maquina['modelo'])}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Endereço IP:*\n{str(informacoes_maquina['ip'])}"
                        }
                    ]
                },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "RESUMO DE RECURSOS"
                }
            },
            {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            # Garante que CPU seja string
                            "text": f"*CPU (Processador):*\n{str(informacoes_componentes['CPU'])} núcleos"
                        },
                        {
                            "type": "mrkdwn",
                            # Garante que RAM seja string
                            "text": f"*Memória RAM:*\n{str(informacoes_componentes['RAM'])} GB"
                        },
                        {
                            "type": "mrkdwn",
                            # Garante que DISCO seja string
                            "text": f"*DISCO DURO:*\n{str(informacoes_componentes['DISCO'])} GB"
                        }
                    ]
                },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Acessar Paineis",
                        },
                        "style": "primary",
                        "url": f"{LINK_HOME}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Ver Detalhes",
                        },
                        "style": "danger",
                        "url": f"{LINK_PAINEL}/{idMaquina}"
                    }
                ]
            }
        ]
    }
    
    return blocks_container["blocks"]


def enviar_notificacao_slack(ID_CNAAL_SLACK: str, alerta_descricao: dict, maquina_data:dict ):
    """ Envia notificação real para o Slack usando a chave 'blocks'. """
    global slack_client
    if not slack_client:
        print("[SLACK] AVISO: O cliente Slack não está inicializado. Notificação ignorada.")
        return

    if not ID_CNAAL_SLACK:
        registrar_log_evento(f"ERRO SLACK: Tentativa de envio sem 'channel_id'. Alerta: {alerta_descricao['sub-titulo']}...", False, None, 'ERRO SLACK')
        return

    blocks_payload = formatar_mensagem_alerta(
        maquina_data["idMaquina"], 
        alerta_descricao, 
        maquina_data["dados_sistema"],
        maquina_data["nomeMaquina"], 
        maquina_data["dados_hardware"]
        ) 
    
    text_fallback = alerta_descricao["sub-titulo"]

    try:
        response = slack_client.chat_postMessage(
            channel=ID_CNAAL_SLACK,
            text=text_fallback,        
            blocks=blocks_payload     
        )
        print(f"[SLACK] Notificação enviada com sucesso para o canal {ID_CNAAL_SLACK}.")
        
    except SlackApiError as e:
        error_msg = f"Falha ao enviar notificação Slack para o canal {ID_CNAAL_SLACK}: {e.response.get('error', str(e))}"
        print(f"[SLACK] ERRO: {error_msg}")
        registrar_log_evento(error_msg, True, None, 'ERRO SLACK')
    except Exception as e:
        error_msg = f"Erro inesperado ao enviar notificação Slack: {str(e)}"
        print(f"[SLACK] ERRO: {error_msg}")
        registrar_log_evento(error_msg, True, None, 'ERRO SLACK')

def notificar_suporte_interno(canal_suporte_id: str, mensagem_erro: str, link_jira: str, nome_maquina: str):
    """
    Envia o alerta TÉCNICO para o canal fixo da equipe Oberon.
    """
    if not slack_client or not canal_suporte_id:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 CRASH: AGENTE PYTHON OBERON PAROU"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Máquina:*\n{nome_maquina}"},
                {"type": "mrkdwn", "text": "*Status:*\n❌ Inoperante"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": f"*Erro Técnico:*\n`{str(mensagem_erro)[:500]}`" 
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": f" *Chamado Jira Criado*\n<{link_jira}|Clique aqui para ver logs e detalhes>"
            }
        }
    ]

    try:
        slack_client.chat_postMessage(channel=canal_suporte_id, text="Erro Crítico - Suporte", blocks=blocks)
        print(f"[SLACK] Notificação técnica enviada para o suporte (Canal {canal_suporte_id}).")
    except Exception as e:
        print(f"[SLACK] Erro ao notificar suporte: {e}")


def notificar_cliente_amigavel(canal_cliente_id: str, nome_maquina: str):
    """
    Envia um aviso AMIGÁVEL para o canal do cliente (banco de dados).
    """
    if not slack_client or not canal_cliente_id:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Aviso de Instabilidade"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": f"Detectamos uma interrupção no monitoramento da máquina *{nome_maquina}*."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": " *Não se preocupe!* Nossa equipe de suporte já recebeu o alerta automático e está trabalhando para restabelecer o serviço o mais rápido possível."
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Oberon • Sistema de Monitoramento 24h • Equipe de Suporte"}
            ]
        }
    ]

    try:
        slack_client.chat_postMessage(channel=canal_cliente_id, text="Aviso de Instabilidade Oberon", blocks=blocks)
        print(f"[SLACK] Notificação amigável enviada para o cliente (Canal {canal_cliente_id}).")
    except Exception as e:
        print(f"[SLACK] Erro ao notificar cliente: {e}")