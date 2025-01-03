import time
import threading
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import sys
import socket
import winreg as reg  # Para adicionar ao registro no Windows
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Configurações de e-mail (SUBSTITUA COM SUAS CREDENCIAIS)
EMAIL_REMETENTE = "Suas Informações"
EMAIL_SENHA = "Suas Informações"  # Substitua pela sua senha de app
EMAIL_DESTINATARIO = "Suas Informações"

tempo_inicial = time.time()
horas_totais = 0
ultima_log_50h = 0
nome_maquina = socket.gethostname()  # Agora obtemos automaticamente o nome da máquina
pendencias_dir = "pendentes"
pendencias_file = os.path.join(pendencias_dir, "emails_pendentes.txt")
email_enviado = False  # Variável global para evitar envio repetido

# Funções de log e envio de e-mails
def salvar_email_pendente(caminho_arquivo, assunto, corpo):
    """Salva os dados do e-mail pendente em um arquivo."""
    os.makedirs(pendencias_dir, exist_ok=True)  # Garante que a pasta 'pendentes' exista
    with open(pendencias_file, "a") as arquivo:
        arquivo.write(f"{assunto}||{caminho_arquivo}||{corpo}\n")

def reenviar_emails_pendentes():
    """Tenta reenviar os e-mails salvos como pendentes."""
    if not os.path.exists(pendencias_file):
        return

    with open(pendencias_file, "r") as arquivo:
        linhas = arquivo.readlines()

    if not linhas:
        return

    emails_reenviados = []
    for linha in linhas:
        try:
            assunto, caminho_arquivo, corpo = linha.strip().split("||")
            enviar_email(caminho_arquivo, assunto, corpo)
            emails_reenviados.append(linha)
        except Exception as e:
            print(f"Erro ao reenviar e-mail pendente: {e}")

    # Remove os e-mails que foram reenviados com sucesso
    with open(pendencias_file, "w") as arquivo:
        for linha in linhas:
            if linha not in emails_reenviados:
                arquivo.write(linha)

def enviar_email(caminho_arquivo, assunto=None, corpo=""):
    """Envia um e-mail e salva em pendentes em caso de falha."""
    global nome_maquina
    assunto = assunto or f"Log de Manutenção - 500 Horas ({nome_maquina})"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg['Subject'] = assunto

    with open(caminho_arquivo, "r") as arquivo:
        anexo = MIMEBase('application', "octet-stream")
        anexo.set_payload(arquivo.read())
        encoders.encode_base64(anexo)
        anexo.add_header('Content-Disposition', f"attachment; filename= manutencao_500h_{nome_maquina}.txt")
        msg.attach(anexo)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())
        server.quit()
        print("Email enviado com sucesso!")
        gerar_log("Email enviado com sucesso!", "importante")
    except smtplib.SMTPAuthenticationError:
        print("Erro de autenticação. Verifique suas credenciais de e-mail.")
        gerar_log("Erro de autenticação no envio de e-mail.", "importante")
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        gerar_log(f"Erro ao enviar o email: {e}", "importante")
        salvar_email_pendente(caminho_arquivo, assunto, corpo)

def gerar_log(mensagem, pasta="log"):
    global nome_maquina
    nome_arquivo = "contador.txt"
    if pasta == "importante":
        nome_arquivo = "manutencao_500h.txt"
    caminho_arquivo = os.path.join(pasta, nome_arquivo)
    mensagem_log = f"{datetime.now()} - {nome_maquina}: {mensagem}\n"
    os.makedirs(pasta, exist_ok=True)
    with open(caminho_arquivo, "a") as arquivo_log:
        arquivo_log.write(mensagem_log)
    print(mensagem_log.strip())

def verificar_500_horas():
    global horas_totais, email_enviado

    # Envia o e-mail para cada múltiplo de 500 horas
    if horas_totais >= 500 and horas_totais % 500 == 0 and not email_enviado:
        gerar_log("Máquina chegou ao total de 500 horas de uso, fazer manutenção!", "importante")
        caminho_arquivo_importante = os.path.join("importante", "manutencao_500h.txt")
        enviar_email(caminho_arquivo_importante)
        email_enviado = True  # Marca que o e-mail foi enviado para este múltiplo de 500 horas

    # Reseta a variável email_enviado quando não for múltiplo de 500 horas
    if horas_totais % 500 != 0:
        email_enviado = False

def loop_log():
    global horas_totais, ultima_log_50h
    while True:
        time.sleep(3600)  # Executar a cada 1 hora
        horas_totais += 1  # Incrementa uma hora por iteração
        horas_desde_ultimo_log_50h = horas_totais - ultima_log_50h
        if horas_desde_ultimo_log_50h >= 50:
            gerar_log(f"O contador está funcionando há {horas_totais:02} horas e está funcionando perfeitamente.")
            ultima_log_50h = horas_totais
        verificar_500_horas()

# Função para acessar arquivos no executável empacotado
def resource_path(relative_path):
    """ Retorna o caminho absoluto do recurso, considerando que pode ser empacotado com PyInstaller. """
    try:
        base_path = sys._MEIPASS  # PyInstaller cria uma pasta temporária para os arquivos incluídos
    except Exception:
        base_path = os.path.abspath(".")  # Caminho padrão quando não está empacotado

    return os.path.join(base_path, relative_path)

# Função para adicionar ao Registro do Windows
def add_to_startup():
    exe_path = os.path.abspath(sys.argv[0])
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE) as reg_key:
        reg.SetValueEx(reg_key, "MeuApp", 0, reg.REG_SZ, exe_path)

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Contador de Horas")
        self.setGeometry(100, 100, 803, 454)  # Definir tamanho inicial
        layout = QVBoxLayout()

        # WebView para carregar o HTML
        self.webview = QWebEngineView()
        layout.addWidget(self.webview)

        self.setLayout(layout)

        # Carregar o HTML automaticamente quando a janela for exibida
        html_file_path = resource_path(os.path.join("assets", "index.html"))
        if os.path.exists(html_file_path):
            with open(html_file_path, "r", encoding="utf-8") as html_file:
                html_content = html_file.read()
            self.webview.setHtml(html_content)

    def closeEvent(self, event):
        QMessageBox.warning(self, "Aviso", "Este aplicativo não pode ser fechado!")
        event.ignore()

# Função para rodar a aplicação PyQt5
def run_pyqt():
    app_qt = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app_qt.exec_())

if __name__ == "__main__":
    os.makedirs("log", exist_ok=True)
    os.makedirs("importante", exist_ok=True)
    os.makedirs(pendencias_dir, exist_ok=True)

    # Adicionar ao Registro do Windows
    add_to_startup()

    # Inicia a thread para o log
    log_thread = threading.Thread(target=loop_log)
    log_thread.daemon = True
    log_thread.start()

    # Tenta reenviar emails pendentes ao iniciar
    reenviar_emails_pendentes()

    # Inicia a aplicação PyQt5
    run_pyqt()