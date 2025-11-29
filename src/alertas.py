# src/alertas.py

from utils.Database import Fazer_consulta_banco
from src.log_evento import registrar_log_evento

def inserir_registro_de_metrica(valor: float, fkComponente: int) -> int:
    """ Insere o Registro e retorna o ID. """
    try:
        id_registro = Fazer_consulta_banco({
            "query": "INSERT INTO Registro (valor, fkComponente) VALUES (%s, %s);",
            "params": (valor, fkComponente),
        })
        if id_registro > 0:
            print(f"   [DB] Registro de métrica inserido com sucesso para componente {fkComponente}. ID: {id_registro}")
        return id_registro
    except RuntimeError as e:
        registrar_log_evento(f"ERRO BD CRÍTICO: Falha ao inserir Registro: {str(e)}", False)
        return -1

def processar_alerta_leitura(idRegistro: int, idParametro: int, tipo: str, valor: float, limite: float, nivel: str, fkLogSistema: int):
    """ Processa o limite e insere o Alerta no DB. """
    alerta_ativo = None
    diferenca =  abs(limite - valor) 
    descricao = None
    titulo_notificacao = None
    if(nivel == "ACEITÁVEL"):
        if(valor < limite):
            nivel = "OCIOSO"
            titulo_notificacao = "ALERTA OCIOSO DE MONITORAMENTO"
            alerta_ativo = True
            descricao = f"Uso de {tipo} está abaixo do nivel aceitavél, se encontra em estado oscioso ({limite:.2f}%). Valor atual: {valor:.2f}% ({diferenca}%  Abaixo do Limite)."
    else:
        alerta_ativo = valor >= limite

    if alerta_ativo:
        if descricao is None:
            descricao = f"Uso de {tipo} atingiu o limite de {nivel} ({limite:.2f}%). Valor atual: {valor:.2f}%.  _({diferenca:.2f}% Acima do Limite)_"
        if titulo_notificacao is None:
            titulo_notificacao = f"ALERTA {nivel} DE MONITORAMENTO"
        try:

            id_alerta = Fazer_consulta_banco({
                "query": "INSERT INTO Alerta (fkRegistro, fkParametro, descricao, nivel) VALUES (%s, %s, %s, %s);",
                "params": (idRegistro, idParametro, descricao, nivel),
            })

            if id_alerta > 0:
                print(f"   Alerta ABERTO para {tipo} (nível: {nivel}). ID Alerta: {id_alerta}")
                registrar_log_evento(f"Alerta ABERTO ({nivel}) para {tipo}. ID={id_alerta}", True, fkLogSistema, 'LOG ALERTA')
            else:
                registrar_log_evento(f"ERRO: Falha ao inserir Alerta para {tipo} no DB.", True, fkLogSistema, 'ERRO ALERTA')
            return {
                "titulo": titulo_notificacao, 
                "sub-titulo": descricao
            }
        except RuntimeError as e:
            registrar_log_evento(f"ERRO BD CRÍTICO ao gerar alerta para {tipo}: {str(e)}", True, fkLogSistema, 'ERRO ALERTA')

