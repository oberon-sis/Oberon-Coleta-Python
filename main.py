# main.py
import time
from utils.display_utils import formatar_palavra
from src.log_evento import registrar_log_evento
from src.log_sistema_detalhe import iniciar_sessao_log_sistema, finalizar_sessao_log_sistema, inserir_detalhe_de_evento
from src.maquina_config import buscar_e_validar_maquina, obter_parametros_monitoramento
from src.alertas import inserir_registro_de_metrica, processar_alerta_leitura
from src.captura import capturar_dado_da_metrica
from src.slack_service import procurar_informacoes_slack, enviar_notificacao_slack, notificar_suporte_interno, notificar_cliente_amigavel
from src.slack_service import enviar_notificacao_slack
from src.incidente import criar_incidente_e_anexar_log

import traceback
# Constantes de Configuração
INTERVALO_DE_COLETA_SEGUNDOS = 200

# Variáveis de estado global (simples)
maquina_data = None
fkLogSistema = None
slackInfo = None

logo = """
║════════════════════════════════════════════════════════════════════════════════════════╣
║     ███████     ███████████   ██████████  ███████████       ███████     ██████   █████ ║
║   ███▒▒▒▒▒███  ▒▒███▒▒▒▒▒███ ▒▒███▒▒▒▒▒█ ▒▒███▒▒▒▒▒███    ███▒▒▒▒▒███  ▒▒██████ ▒▒███  ║ 
║  ███     ▒▒███  ▒███    ▒███  ▒███  █ ▒   ▒███    ▒███   ███     ▒▒███  ▒███▒███ ▒███  ║
║ ▒███      ▒███  ▒██████████   ▒██████     ▒██████████   ▒███      ▒███  ▒███▒▒███▒███  ║
║ ▒███      ▒███  ▒███▒▒▒▒▒███  ▒███▒▒█     ▒███▒▒▒▒▒███  ▒███      ▒███  ▒███ ▒▒██████  ║
║ ▒▒███     ███   ▒███    ▒███  ▒███ ▒   █  ▒███    ▒███  ▒▒███     ███   ▒███  ▒▒█████  ║
║ ▒▒▒███████▒    ███████████   ██████████  █████   █████  ▒▒▒███████▒    █████  ▒▒█████  ║
║  ▒▒▒▒▒▒▒     ▒▒▒▒▒▒▒▒▒▒▒   ▒▒▒▒▒▒▒▒▒▒  ▒▒▒▒▒   ▒▒▒▒▒     ▒▒▒▒▒▒▒     ▒▒▒▒▒    ▒▒▒▒▒    ║  
║════════════════════════════════════════════════════════════════════════════════════════╣
║                      SISTEMA DE MONITORAMENTO DA OBERON                                ║
║════════════════════════════════════════════════════════════════════════════════════════╣
    Iniciando Monitoramento ....
╚════════════════════════════════════════════════════════════════════════════════════════╝
    """
menu_resumido = """
    """
saida = """
    ╔════════════════════════════════════════════════════╗
    ║             Encerrando a OBERON System             ║
    ║════════════════════════════════════════════════════╣
    ║  Sessão finalizada com sucesso.                    ║
    ║  Todos os serviços foram encerrados.               ║
    ║  Até a próxima utilização.                         ║
    ╚════════════════════════════════════════════════════╝
    """

ID_CANAL_SUPORTE_OBERON = "C0A0FAW0M2R"

ID_CANAL_SLACK_CLIENTE = None

def main():
    global fkLogSistema
    global logo
    global maquina_data
    
    erro_fatal = None
    try:
        print(logo)
        orquestrar_coleta()
        
    except KeyboardInterrupt:
        formatar_palavra("\nMonitoramento Interrompido pelo Usuário.")
    except Exception as e:
        erro_fatal = str(e)
        formatar_palavra(f"\nERRO CRÍTICO NO AGENTE: {erro_fatal}")
        traceback.print_exc()
    finally:
        if fkLogSistema is not None and fkLogSistema != -1:
            
            if erro_fatal:
                registrar_log_evento(f"Iniciando protocolo de incidente: {erro_fatal}", False)
                
                chave_jira, link_jira = criar_incidente_e_anexar_log(
                    titulo=f"Crash Agente - {maquina_data['nomeMaquina'] if maquina_data else 'S/N'}",
                    descricao=f"Erro fatal: {erro_fatal}",
                    fkLogSistema=fkLogSistema
                )

                nome_maquina = maquina_data['nomeMaquina'] if maquina_data else "Máquina Desconhecida"

                print("Enviando alerta para o Suporte Interno...")
                notificar_suporte_interno(
                    canal_suporte_id=ID_CANAL_SUPORTE_OBERON, 
                    mensagem_erro=erro_fatal, 
                    link_jira=link_jira,
                    nome_maquina=nome_maquina
                )

                if ID_CANAL_SLACK_CLIENTE:
                    print(f"Enviando aviso para o Cliente (Canal {ID_CANAL_SLACK_CLIENTE})...")
                    notificar_cliente_amigavel(
                        canal_cliente_id=ID_CANAL_SLACK_CLIENTE,
                        nome_maquina=nome_maquina
                    )
            
            # Finaliza sessão no banco
            inserir_detalhe_de_evento(fkLogSistema, 'Desligamento', 'Agente finalizado.')
            finalizar_sessao_log_sistema(fkLogSistema)
          
            print("\n ATENÇÃO: O AGENTE ENCERROU INESPERADAMENTE. VERIFIQUE OS LOGS ACIMA.")
            print("\n CASO TENHA DADO ERRO AO ENCONTRAR O MAC ADRESS, ATUALIZAR OS DADOS DESTA MAQUINA OU FAZER O CADASTRO")
            print("\n ATUALIZAR OS DADOS DESTA MAQUINA OU FAZER O CADASTRO.")
            input("\nPressione Enter para sair...")
            

def orquestrar_coleta():
    """ Orquestrador principal funcional. """
    global maquina_data
    global fkLogSistema
    global slackInfo 
    global ID_CANAL_SLACK_CLIENTE
    
    maquina_data = buscar_e_validar_maquina()
    
    if maquina_data is None:
        return

    fkLogSistema = iniciar_sessao_log_sistema(maquina_data['idMaquina'])
    if fkLogSistema == -1:
        registrar_log_evento("Falha crítica: Não foi possível iniciar a sessão LogSistema.", False, None, 'ERRO INICIAL')
        return

    registrar_log_evento(f"Monitoramento iniciado. Sessão: {fkLogSistema}", True, fkLogSistema, 'LOG INICIO')

    # 2. CARREGAR PARÂMETROS
    parametros = obter_parametros_monitoramento(maquina_data['idMaquina'])
    
    if not parametros:
        registrar_log_evento("Nenhum parâmetro configurado. Encerrando.", True, fkLogSistema, 'LOG GERAL')
        return

    ID_CANAL_SLACK_CLIENTE = procurar_informacoes_slack(maquina_data['idMaquina'])

    if ID_CANAL_SLACK_CLIENTE is None or len(ID_CANAL_SLACK_CLIENTE) < 10:
        registrar_log_evento("Nenhum Canal encontrado", True, fkLogSistema, 'LOG GERAL')
        return 

    # ---------------------------------------------------------
    #  LINHA DE TESTE -- para testar a criação de incidentes
    # Isso vai forçar o código a falhar assim que iniciar a coleta
    # raise Exception("TESTE DE CRASH: Verificando abertura de chamado no Jira e Slack")
    # ---------------------------------------------------------
    while True:
        registrar_log_evento("Iniciando novo ciclo de coleta...", True, fkLogSistema, 'LOG COLETA')
        print('╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗')
        
        for tipo, lista_parametros in parametros.items():
            
            valor_dado = capturar_dado_da_metrica(tipo, fkLogSistema)

            if valor_dado is None:
                 continue
            
            fkComponente = lista_parametros[0]['fkComponente']

            idRegistro = inserir_registro_de_metrica(valor_dado, fkComponente)
            
            if idRegistro != -1:
                for medida in lista_parametros:
                    
                    print(f"   - Coleta: {tipo} ({medida['unidade']}) → Valor: {valor_dado:.2f} {medida['unidade']} → Limite Configurado ({medida['nivel']}): {medida['limite']}")
                    
                    alerta_descricao = processar_alerta_leitura(
                        idRegistro, medida['idParametro'], tipo, valor_dado, 
                        medida['limite'], medida['nivel'], fkLogSistema
                    )

                    if alerta_descricao is not None:
                        enviar_notificacao_slack(ID_CANAL_SLACK_CLIENTE, alerta_descricao, maquina_data )
        
        print('\n╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════╝')
        time.sleep(INTERVALO_DE_COLETA_SEGUNDOS)





if __name__ == '__main__':
    main()