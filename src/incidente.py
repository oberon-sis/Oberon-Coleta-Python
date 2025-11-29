# src/incidente.py
import os
from jira import JIRA
from src.log_evento import registrar_log_evento, LOG_FILE_PATH
from utils.Database import Fazer_consulta_banco

# Carrega variáveis de ambiente
JIRA_URL = os.getenv('JIRA_URL')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY', 'OBERON')

def criar_incidente_e_anexar_log(titulo: str, descricao: str, fkLogSistema: int):
    """
    Cria um ticket no Jira.
    Anexa o arquivo de logs local.
    Registra na tabela 'LogIncidente' do banco para rastreabilidade.
    
    Retorna: (chave_jira, link_jira) ou (None, None) em caso de erro.
    """
    
    if not all([JIRA_URL, JIRA_USER, JIRA_API_TOKEN]):
        msg = "Credenciais do Jira não configuradas. Incidente não será criado."
        print(f"⚠️ {msg}")
        registrar_log_evento(msg, True, fkLogSistema, 'ERRO JIRA')
        return None, None

    chave_jira = None
    link_jira = None

    try:
        jira_options = {'server': JIRA_URL}
        jira = JIRA(options=jira_options, basic_auth=(JIRA_USER, JIRA_API_TOKEN))

        issue_dict = {
            'project': {'key': JIRA_PROJECT_KEY},
            'summary': f'[ALERTA OBERON] {titulo}',
            'description': f"{descricao}\n\n*ID Sessão LogSistema:* {fkLogSistema}",
            'issuetype': {'name': 'Report an incident'}, 
        }
        
        new_issue = jira.create_issue(fields=issue_dict)
        chave_jira = new_issue.key
        link_jira = f"{JIRA_URL}/browse/{chave_jira}"
        
        registrar_log_evento(f"Ticket Jira criado com sucesso: {chave_jira}", True, fkLogSistema, 'SUCESSO JIRA')

        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'rb') as f:
                jira.add_attachment(issue=new_issue, attachment=f)
            registrar_log_evento(f"Arquivo de log '{LOG_FILE_PATH}' anexado ao ticket.", False)
        else:
            registrar_log_evento("Arquivo de log não encontrado para anexo.", False)

        Fazer_consulta_banco({
            "query": """
                INSERT INTO Incidente (chaveJira, titulo, descricao, linkJira, fkLogSistema, dataCriacao)
                VALUES (%s, %s, %s, %s, %s, NOW());
            """,
            "params": (chave_jira, titulo, descricao, link_jira, fkLogSistema)
        })
        
        registrar_log_evento(f"[DB] Rastreabilidade gravada na tabela LogIncidente para {chave_jira}.", False)

        return chave_jira, link_jira

    except Exception as e:
        erro_msg = f"Falha ao processar incidente no Jira/DB: {str(e)}"
        print(f"❌ {erro_msg}")
        registrar_log_evento(erro_msg, True, fkLogSistema, 'ERRO CRITICO')
        return None, None