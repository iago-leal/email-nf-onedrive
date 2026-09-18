-- Registro de processados (data-delta.md, versão 1 do esquema).

CREATE TABLE IF NOT EXISTS anexos (
    id               INTEGER PRIMARY KEY,
    caixa_endereco   TEXT NOT NULL,
    caixa_indice     INTEGER NOT NULL,
    message_id       TEXT NOT NULL,
    sha256           TEXT NOT NULL,
    nome_original    TEXT NOT NULL,
    remetente        TEXT NOT NULL,
    assunto          TEXT NOT NULL,
    data_mensagem    TEXT NOT NULL,
    classe           TEXT NOT NULL
                     CHECK (classe IN ('nfe-xml', 'palavra-chave', 'sem-classificacao')),
    estado           TEXT NOT NULL
                     CHECK (estado IN ('extraido', 'enviado', 'falha-envio', 'retido')),
    caminho_destino  TEXT,
    tentativas_envio INTEGER NOT NULL DEFAULT 0,
    ultimo_erro      TEXT,
    criado_em        TEXT NOT NULL,
    atualizado_em    TEXT NOT NULL,
    UNIQUE (caixa_endereco, message_id, sha256)
);

CREATE INDEX IF NOT EXISTS anexos_janela
    ON anexos (caixa_endereco, estado, data_mensagem);

CREATE TABLE IF NOT EXISTS ocorrencias (
    caixa_endereco TEXT NOT NULL,
    message_id     TEXT NOT NULL,
    tipo           TEXT NOT NULL CHECK (tipo IN ('sem-anexo', 'compactado')),
    registrado_em  TEXT NOT NULL,
    PRIMARY KEY (caixa_endereco, message_id, tipo)
);

CREATE TABLE IF NOT EXISTS avisos (
    causa               TEXT PRIMARY KEY,
    primeira_ocorrencia TEXT NOT NULL,
    ultimo_aviso        TEXT,
    ativa               INTEGER NOT NULL CHECK (ativa IN (0, 1)),
    mensagem            TEXT NOT NULL,
    entrega_pendente    INTEGER NOT NULL CHECK (entrega_pendente IN (0, 1))
);

CREATE TABLE IF NOT EXISTS meta (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
