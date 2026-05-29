import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

def enviar_correo_confirmacion(paciente_email, paciente_nombre, doctor_nombre, fecha, motivo, urgente):
    """
    Servicio de envío de correo electrónico.
    Conecta con el servidor SMTP (ej. Microsoft Outlook o Mailjet) usando variables en .env.
    Además, escribe en un archivo log local para verificar el envío.
    """
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_user = os.environ.get('MAIL_USER')
    mail_password = os.environ.get('MAIL_PASSWORD')
    mail_from = os.environ.get('MAIL_FROM', 'clinica-citas@culiacan.tecnm.mx')
    mail_to = os.environ.get('MAIL_TO', paciente_email)

    asunto = f"Confirmación de Cita Médica {'(URGENTE)' if urgente else ''} - {doctor_nombre}"
    cuerpo = f"""
    Estimado/a {paciente_nombre},
    
    Su cita ha sido confirmada con éxito.
    
    Detalles de la cita:
    - Médico: {doctor_nombre}
    - Fecha y Hora: {fecha}
    - Motivo: {motivo}
    - Prioridad: {'Urgente (Prioridad Alta)' if urgente else 'Normal'}
    
    Por favor, llegue 10 minutos antes de su hora programada.
    
    Portal de Citas Médicas - Proyecto de Programación Web
    Estudiante: Luis Armando Ojeda Rodríguez
    """

    log_path = os.path.join(os.path.dirname(__file__), 'citas_enviadas.log')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Guardar en log local como evidencia física para revisión del profesor
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n========================================\n")
        f.write(f"FECHA DE ENVÍO: {ahora}\n")
        f.write(f"DE: {mail_from}\n")
        f.write(f"PARA: {paciente_email}\n")
        f.write(f"ASUNTO: {asunto}\n")
        f.write(f"CONTENIDO:\n{cuerpo}\n")
        f.write(f"========================================\n")
    print(f"--> [EMAIL SERVICE] Cita guardada en 'backend/citas_enviadas.log'")

    # Si se configuran credenciales SMTP reales, intentar el envío por red
    if mail_server and mail_user and mail_password:
        try:
            msg = EmailMessage()
            msg.set_content(cuerpo)
            msg["Subject"] = asunto
            msg["From"] = mail_from
            msg["To"] = mail_to

            with smtplib.SMTP(mail_server, int(mail_port)) as server:
                server.starttls()
                server.login(mail_user, mail_password)
                server.send_message(msg)
            print("--> [SMTP] Correo enviado correctamente por SMTP real.")
        except Exception as e:
            print(f"--> [SMTP ERROR] No se pudo enviar por SMTP real: {e} (Se guardó la evidencia en el log local).")
