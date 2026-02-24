"""
Independent models for Worker
Mirrors the backend models for tables the Worker needs access to
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Carteirinha(Base):
    __tablename__ = "carteirinhas"

    id = Column(Integer, primary_key=True, index=True)
    carteirinha = Column(Text, unique=True, nullable=False)
    paciente = Column(Text)
    id_paciente = Column(Integer, index=True)
    id_pagamento = Column(Integer, index=True)
    status = Column(Text, default="ativo")
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    jobs = relationship("Job", back_populates="carteirinha_rel")
    guias = relationship("BaseGuia", back_populates="carteirinha_rel")
    logs = relationship("Log", back_populates="carteirinha_rel")
    convenio_rel = relationship("Convenio")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    carteirinha_id = Column(Integer, ForeignKey("carteirinhas.id", ondelete="CASCADE"))
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="SET NULL"), nullable=True)
    rotina = Column(Text)
    params = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    attempts = Column(Integer, default=0)
    priority = Column(Integer, default=0)
    locked_by = Column(Text)
    timeout = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    carteirinha_rel = relationship("Carteirinha", back_populates="jobs")
    logs = relationship("Log", back_populates="job_rel")


class BaseGuia(Base):
    __tablename__ = "base_guias"

    id = Column(Integer, primary_key=True, index=True)
    carteirinha_id = Column(Integer, ForeignKey("carteirinhas.id", ondelete="CASCADE"))
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="SET NULL"), nullable=True)
    guia = Column(Text)
    data_autorizacao = Column(Date)
    senha = Column(Text)
    status_guia = Column(Text, default="Autorizado")
    validade = Column(Date)
    codigo_terapia = Column(Text)
    qtde_solicitada = Column(Integer)
    sessoes_autorizadas = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    carteirinha_rel = relationship("Carteirinha", back_populates="guias")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    carteirinha_id = Column(Integer, ForeignKey("carteirinhas.id", ondelete="SET NULL"), nullable=True)
    level = Column(Text, default="INFO")  # INFO, WARN, ERROR
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job_rel = relationship("Job", back_populates="logs")
    carteirinha_rel = relationship("Carteirinha", back_populates="logs")

class Convenio(Base):
    __tablename__ = "convenios"

    id_convenio = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
    usuario = Column(Text)
    senha_criptografada = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PriorityRule(Base):
    __tablename__ = "priority_rules"

    id = Column(Integer, primary_key=True, index=True)
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="CASCADE"))
    rotina = Column(Text)
    base_priority = Column(Integer, default=1)
    weight_per_day = Column(Text) 
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    convenio_rel = relationship("Convenio")

class JobExecution(Base):
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="SET NULL"), nullable=True)
    rotina = Column(Text)
    status = Column(Text)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    items_found = Column(Integer, default=0)
    error_category = Column(Text)
    error_message = Column(Text)

    job_rel = relationship("Job")
    convenio_rel = relationship("Convenio")

class Ficha(Base):
    __tablename__ = "fichas"

    id_ficha = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(Integer)
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="CASCADE"))
    id_procedimento = Column(Integer, ForeignKey("procedimentos.id_procedimento"))
    id_guia = Column(Integer, ForeignKey("base_guias.id"))
    status_assinatura = Column(Text)
    status_conciliacao = Column(Text)

    convenio_rel = relationship("Convenio")
    procedimento_rel = relationship("Procedimento")
    guia_rel = relationship("BaseGuia")

class TipoFaturamento(Base):
    __tablename__ = "tipo_faturamento"

    id_tipo = Column(Integer, primary_key=True, index=True)
    tipo = Column(Text)
    id_doc_autorizacao = Column(Integer)
    id_doc_faturamento = Column(Integer)

class TipoDocumento(Base):
    __tablename__ = "tipo_documentos"

    id_tipo_doc = Column(Integer, primary_key=True, index=True)
    nome = Column(Text)
    uso = Column(Text)

class ModeloDocumento(Base):
    __tablename__ = "modelo_documentos"

    id_modelo = Column(Integer, primary_key=True, index=True)
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="CASCADE"))
    nome_doc = Column(Text)
    id_tipo_faturamento = Column(Integer, ForeignKey("tipo_faturamento.id_tipo"))

    convenio_rel = relationship("Convenio")
    tipo_fat_rel = relationship("TipoFaturamento")

class Procedimento(Base):
    __tablename__ = "procedimentos"

    id_procedimento = Column(Integer, primary_key=True, index=True)
    nome = Column(Text)
    codigo_procedimento = Column(Text)
    autorizacao = Column(Text)
    faturamento = Column(Text)
    status = Column(Text, default="ativo")

class ProcedimentoFaturamento(Base):
    __tablename__ = "procedimento_faturamento"

    id_proc_fat = Column(Integer, primary_key=True, index=True)
    id_procedimento = Column(Integer, ForeignKey("procedimentos.id_procedimento", ondelete="CASCADE"))
    id_convenio = Column(Integer, ForeignKey("convenios.id_convenio", ondelete="CASCADE"))
    valor = Column(Float)
    data_inicio = Column(Date)
    data_fim = Column(Date)
    status = Column(Text, default="ativo")

    procedimento_rel = relationship("Procedimento")
    convenio_rel = relationship("Convenio")

class Area(Base):
    __tablename__ = "areas"

    id_area = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
