# Rastreabilidade: requisitos e cenários → testes

> Feature `001-mvp-email-nf-onedrive`. Fontes: `_reversa_forward/001-mvp-email-nf-onedrive/requirements.md` §5 (RF-01 a RF-20) e §7 (14 cenários).
> Abreviações: `e2e/arq` = `tests/integracao/test_ciclo_arquivamento.py`; `e2e/fal` = `tests/integracao/test_ciclo_falhas.py`; `int/<nome>` = `tests/integracao/test_<nome>.py`; `uni/<nome>` = `tests/unidade/test_<nome>.py`.
> Os testes `e2e` chamam `cli.main` como o `cron` faria, com IMAP e Telegram simulados e o Rclone real gravando num diretório local.
> Estado na geração deste mapa: 217 testes, todos passando.

## Cenários do §7

| # | Cenário | Testes que o cobrem | Observação |
|---|---------|---------------------|------------|
| 1 | Boleto recebido é arquivado sem ação manual | `e2e/arq::test_boleto_arquivado`; `int/coleta::test_so_comandos_de_leitura_e_body_peek`; `uni/mime::test_ignora_imagem_e_reconhece_extensao_maiuscula` | O e2e confirma nome no destino, mensagem não lida, pasta de trabalho vazia, resumo e código 0; o descarte do `.png` é coberto na extração. |
| 2 | Reexecução não duplica documentos | `e2e/arq::test_reexecucao_nao_duplica`; `int/coleta::test_segunda_execucao_nao_entrega_nada_nem_repete_retido` | O segundo verifica a linha "nenhum anexo novo". |
| 3 | Nome repetido com conteúdo diferente | `e2e/arq::test_nome_repetido_recebe_sufixo_e_preserva_o_original`; `int/envio::test_conteudo_diferente_recebe_sufixo_e_preserva_o_original`; `int/rclone::test_copiar_nunca_sobrescreve` | |
| 4 | OneDrive indisponível e retomada automática | `e2e/arq::test_retomada_apos_falha_de_envio`; `int/envio::test_remote_invalido_suspende_os_demais_envios`; `int/coleta::test_anexo_pendente_e_reentregue_sem_duplicar_registro` | A indisponibilidade é simulada com a pasta de destino ausente; a queda real do OneDrive fica para a T042. |
| 5 | Caixa nova incompleta não derruba as demais | `e2e/fal::test_caixa_sem_senha_nao_impede_as_demais`; `uni/configuracao::test_senha_ausente_invalida_so_a_caixa` | |
| 6 | Erro global de configuração aborta antes da rede | `e2e/fal::test_data_inicial_fora_do_formato_aborta_antes_da_rede`; `e2e/fal::test_erro_global_de_configuracao_sem_acesso_a_rede`; `uni/configuracao::test_data_inicial_fora_do_formato` | |
| 7 | Falha persistente não inunda o operador | `e2e/fal::test_supressao_por_6_horas_e_aviso_de_recuperacao`; `uni/avisos::test_mesma_falha_por_3_horas_gera_um_aviso`; `uni/avisos::test_recuperacao_notificada_uma_vez` | |
| 8 | Credenciais nunca vazam | `e2e/fal::test_credenciais_ausentes_do_log_dos_avisos_e_do_verificar_config`; `e2e/fal::test_verificar_config_lista_caixas_com_senha_mascarada`; `uni/segredos` (7 testes); `uni/logs::test_segredo_mascarado_no_arquivo` | |
| 9 | Execuções sobrepostas | `e2e/fal::test_execucoes_sobrepostas`; `uni/trava::test_trava_recente_de_processo_vivo_e_respeitada` | |
| 10 | Simulação não produz efeitos | `e2e/arq::test_simulacao_nao_envia_nao_registra_nem_avisa`; `e2e/arq::test_simulacao_com_registro_existente_nao_o_altera`; `int/envio::test_simulacao_nao_envia_nem_altera_registro` | O e2e usa um anexo, não dois. |
| 11 | Anexo não reconhecido fica retido para revisão | `e2e/arq::test_documento_sem_classificacao_fica_retido`; `int/coleta::test_sem_classificacao_e_retido_e_nao_vai_para_envio`; `int/coleta::test_segunda_execucao_nao_entrega_nada_nem_repete_retido` | O último garante o registro uma única vez em duas execuções. |
| 12 | Documento sem anexo e anexo compactado | `e2e/arq::test_sem_anexo_e_compactado_registrados_uma_vez`; `int/coleta::test_sem_anexo_e_compactado_registrados_uma_vez` | |
| 13 | Teste de escrita no OneDrive | `e2e/fal::test_testar_onedrive`; `int/envio::test_testar_onedrive`; `int/envio::test_testar_onedrive_destino_ausente` | Contra o OneDrive real: `onboarding.md` §3. |
| 14 | Instalação por terceiro | sem teste automatizado | `docs/instalacao-e-operacao.md` e `onboarding.md` §1 a §8, verificados na T042. |

## Requisitos funcionais

| RF | Resumo | Testes | Verificação manual |
|----|--------|--------|--------------------|
| RF-01 | Descoberta de `EMAIL<n>` com lacunas e padrões | `uni/configuracao::test_numeracao_com_lacuna`, `test_pasta_servidor_e_destino_por_caixa`, `test_caixas_ordenadas_por_indice`, `test_variaveis_parecidas_nao_viram_caixa`, `test_env_atual_so_com_email1_funciona` | |
| RF-02 | Validação antes da rede; erro global versus erro de caixa | `uni/configuracao::test_erros_globais_sao_reunidos`, `test_variavel_global_ausente_aborta`, `test_senha_ausente_invalida_so_a_caixa`, `test_endereco_invalido`, `test_endereco_duplicado_na_mesma_pasta`; `e2e/fal::test_erro_global_de_configuracao_sem_acesso_a_rede`, `test_data_inicial_fora_do_formato_aborta_antes_da_rede` | |
| RF-03 | Segredos nunca exibidos; `verificar-config` | `uni/segredos` (7 testes); `uni/configuracao::test_repr_nao_expoe_segredos`, `test_segredos_ficam_registrados_para_mascaramento`; `uni/avisos::test_mensagem_nunca_contem_segredos`; `uni/logs::test_segredo_mascarado_no_arquivo`; `e2e/fal::test_credenciais_ausentes_do_log_dos_avisos_e_do_verificar_config`, `test_verificar_config_lista_caixas_com_senha_mascarada` | `onboarding.md` §6, passo 4 |
| RF-04 | Conexão cifrada e somente leitura | `int/coleta::test_so_comandos_de_leitura_e_body_peek`; `e2e/arq::test_boleto_arquivado` | `onboarding.md` §4 (Gmail real) |
| RF-05 | Data de corte da busca | `uni/janela` (6 testes); `int/coleta::test_janela_respeita_data_inicial`, `test_anexo_pendente_e_reentregue_sem_duplicar_registro` | |
| RF-06 | Extração de PDF e XML, encaminhados, compactados sinalizados | `uni/mime` (11 testes); `int/coleta::test_extrai_classifica_e_grava_na_pasta_de_trabalho`; `e2e/arq::test_sem_anexo_e_compactado_registrados_uma_vez` | |
| RF-07 | Classificação e retenção dos não reconhecidos | `uni/classificacao` (15 testes); `int/coleta::test_sem_classificacao_e_retido_e_nao_vai_para_envio`; `e2e/arq::test_documento_sem_classificacao_fica_retido` | `onboarding.md` §4 (conferir retidos reais) |
| RF-08 | Registro persistente e não reenvio | `uni/registro` (19 testes); `e2e/arq::test_reexecucao_nao_duplica` | |
| RF-09 | "Possível documento sem anexo" | `int/coleta::test_sem_anexo_e_compactado_registrados_uma_vez`; `e2e/arq::test_sem_anexo_e_compactado_registrados_uma_vez` | |
| RF-10 | Nome padronizado, saneado, até 200 caracteres | `uni/nomeacao` (40 testes) | Convenção da pasta `CONTAS A PAGAR`, L-03 fechada em 2026-09-21 (`docs/onedrive/estrutura-contas-a-pagar.md` §3) |
| RF-11 | Sem sobrescrita; sufixo; idêntico já presente | `int/envio::test_conteudo_diferente_recebe_sufixo_e_preserva_o_original`, `test_arquivo_identico_ja_presente_nao_e_reenviado`, `test_dois_anexos_de_mesmo_nome_na_mesma_execucao`; `int/rclone::test_copiar_nunca_sobrescreve`; `e2e/arq::test_nome_repetido_recebe_sufixo_e_preserva_o_original` | |
| RF-12 | Confirmação no destino; `falha-envio` e nova tentativa | `int/envio::test_envio_novo_confirma_registra_e_apaga_copia_local`, `test_destino_inexistente_nao_e_criado`, `test_aviso_apos_cinco_tentativas`; `e2e/arq::test_retomada_apos_falha_de_envio` | |
| RF-13 | Cópia local apagada após a confirmação | `int/envio::test_envio_novo_confirma_registra_e_apaga_copia_local`; `e2e/arq::test_boleto_arquivado`; `e2e/fal::test_excecao_nao_prevista` | |
| RF-14 | `testar-onedrive` | `int/envio::test_testar_onedrive`, `test_testar_onedrive_destino_ausente`; `int/rclone::test_deletefile_so_no_arquivo_de_teste`; `e2e/fal::test_testar_onedrive` | `onboarding.md` §3 (OneDrive real, T042) |
| RF-15 | Ponto de entrada, subcomandos e `--simular` | `e2e/arq::test_simulacao_nao_envia_nao_registra_nem_avisa`, `test_simulacao_com_registro_existente_nao_o_altera`; `e2e/fal::test_verificar_config_lista_caixas_com_senha_mascarada`, `test_home_por_variavel_de_ambiente` | |
| RF-16 | Sem sobreposição; trava abandonada após 25 min | `uni/trava` (10 testes); `e2e/fal::test_execucoes_sobrepostas`, `test_trava_abandonada_e_removida` | `onboarding.md` §7 |
| RF-17 | Códigos de saída 0, 1 e 2 | `e2e/fal::test_senha_errada_so_na_caixa_2_sai_com_codigo_1`, `test_caixa_sem_senha_nao_impede_as_demais`, `test_todas_as_caixas_com_falha_sai_com_codigo_2`, `test_erro_global_de_configuracao_sem_acesso_a_rede`, `test_excecao_nao_prevista`, `test_disco_cheio` | |
| RF-18 | Log com rotação de 30 dias e resumo | `uni/logs::test_rotacao_diaria_com_30_arquivos`, `test_linha_iso_nivel_caixa_e_permissao_600`; `e2e/arq::test_boleto_arquivado`, `test_reexecucao_nao_duplica` | A rotação real em 31 dias não é exercitada; o teste fixa a configuração do handler. `onboarding.md` §8 |
| RF-19 | Aviso no Telegram, supressão de 6 h, recuperação | `uni/avisos` (12 testes); `e2e/fal::test_supressao_por_6_horas_e_aviso_de_recuperacao`, `test_telegram_fora_do_ar_reenvia_na_execucao_seguinte`, `test_senha_errada_so_na_caixa_2_sai_com_codigo_1` | `onboarding.md` §6 (bot real) |
| RF-20 | Guia de instalação e `.env.example` | sem teste automatizado | `docs/instalacao-e-operacao.md`, `.env.example`; instalação por terceiro na T042 |

## Casos de borda sem requisito próprio

| Caso | Testes |
|------|--------|
| XML truncado com raiz de NF-e não é NF-e (CE EC-07, desvio da D-07) | `uni/classificacao::test_xml_malformado_nao_e_nfe`, `test_xml_malformado_cai_nas_regras_de_texto` |
| Pasta IMAP com acento, em UTF-7 modificado | `int/coleta::test_pasta_com_acento_e_codificada`; `uni/classificacao::test_utf7_ida_e_volta` |
| Pasta IMAP inexistente lista as pastas no log | `int/coleta::test_pasta_inexistente_lista_as_pastas` |
| Servidor IMAP fora do ar | `int/coleta::test_servidor_fora_do_ar`; `e2e/fal::test_todas_as_caixas_com_falha_sai_com_codigo_2` |
| Subcomandos destrutivos do Rclone recusados (RN-02) | `int/rclone::test_subcomandos_fora_da_lista_sao_recusados` |
| Registro corrompido nunca é recriado | `uni/registro::test_banco_corrompido_aborta` |
| Exceção não prevista e disco cheio (EM EC-06, EC-07) | `e2e/fal::test_excecao_nao_prevista`, `test_disco_cheio` |

---

# Feature `002-oauth-gmail-google-cloud`

> Fontes: `_reversa_forward/002-oauth-gmail-google-cloud/requirements.md` §5 (RF-01 a RF-14) e §7 (16 cenários).
> Abreviações novas: `e2e/oauth` = `tests/integracao/test_ciclo_oauth.py`; `e2e/oauth-fal` = `tests/integracao/test_ciclo_oauth_falhas.py`; `e2e/autorizar` = `tests/integracao/test_autorizar_caixa.py`; `e2e/caixas` = `tests/integracao/test_cli_caixas.py`; `int/servico` = `tests/integracao/test_autorizacao_servico.py`; `uni/arquivo` = `tests/unidade/test_autorizacao_arquivo.py`; `uni/fluxo` = `tests/unidade/test_autorizacao_fluxo.py`.
> O serviço de autorização do Google é um dublê HTTP em `127.0.0.1` (`ServicoAutorizacaoFalso`), o `AUTHENTICATE XOAUTH2` é atendido pelo `ServidorIMAPFalso`, e o navegador do operador é simulado no teste. Nenhum teste fala com o Google; o que depende do Google real tem roteiro manual no `onboarding.md` da feature.
> Estado na geração deste mapa: 361 testes, todos passando (236 anteriores, sem alteração de expectativa além de `COMANDOS_PERMITIDOS`, e 125 novos).

## Cenários do §7

| # | Cenário | Testes que o cobrem | Observação |
|---|---------|---------------------|------------|
| 1 | Instalação atual segue funcionando sem edição | `uni/configuracao::test_auth_ausente_vale_senha_e_nada_muda`; `e2e/oauth::test_instalacao_sem_oauth_nao_fala_com_o_servico_de_autorizacao`; `e2e/caixas::test_verificar_config_sem_oauth_fica_como_antes` | Os 236 testes da feature 001 seguem verdes. `onboarding.md` §2. |
| 2 | Caixa em oauth dispensa a senha | `uni/configuracao::test_caixa_oauth_dispensa_a_senha_e_e_valida_sem_autorizacao`, `test_senha_presente_em_caixa_oauth_e_ignorada_com_alerta` | |
| 3 | Modo de autenticação inválido | `uni/configuracao::test_auth_invalido_invalida_so_a_caixa`, `test_auth_aceita_maiusculas` | |
| 4 | Credenciais do cliente ausentes | `uni/configuracao::test_credenciais_do_cliente_ausentes_invalidam_so_as_caixas_oauth`, `test_credenciais_do_cliente_sem_caixa_oauth_nao_geram_alerta`; `e2e/oauth-fal::test_credenciais_do_cliente_ausentes_viram_erro_de_configuracao_da_caixa`; `e2e/autorizar::test_credenciais_do_cliente_ausentes` | |
| 5 | Autorização de uma caixa no computador do operador | `e2e/autorizar::test_sucesso_grava_a_autorizacao_e_sai_com_0`, `test_pedido_de_consentimento_e_troca_seguem_o_contrato`, `test_nao_usa_trava_registro_nem_aviso`; `uni/fluxo` (15 testes); `uni/arquivo::test_grava_com_600_em_diretorio_700_criado_sob_demanda` | Com o Google real: `onboarding.md` §5. |
| 6 | Diretório de autorizações configurável | `e2e/autorizar::test_diretorio_de_autorizacoes_configuravel`; `uni/configuracao::test_dir_autorizacoes_relativo_e_absoluto` | |
| 7 | Consentimento dado com a conta errada | `e2e/autorizar::test_conta_divergente_revoga_e_nada_grava`, `test_conta_divergente_com_revogacao_indisponivel`, `test_conta_nao_identificada`, `test_conta_com_maiusculas_diferentes_e_a_mesma_conta` | `onboarding.md` §5, teste negativo 1. |
| 8 | Ciclo completo com caixa em oauth | `e2e/oauth::test_instalacao_mista_coleta_as_caixas_dos_dois_modos`, `test_instalacao_so_com_caixas_oauth`, `test_simulacao_tambem_autentica_por_oauth`; `int/coleta::test_caixa_oauth_conecta_por_xoauth2_sem_login` | `onboarding.md` §7. |
| 9 | Renovação sem intervenção | `e2e/oauth::test_credencial_temporaria_e_renovada_a_cada_execucao`; `int/servico::test_renovacao_devolve_a_credencial_e_a_registra_como_segredo` | O prazo real de 1 h só se verifica à mão: `onboarding.md` §7. |
| 10 | Autorização revogada pelo titular | `e2e/oauth-fal::test_invalid_grant_pede_nova_autorizacao_e_preserva_o_arquivo`, `test_autorizacao_ausente`, `test_autorizacao_de_outro_cliente_oauth`, `test_authenticate_recusado_pelo_servidor_de_email`; `int/coleta::test_xoauth2_recusado_responde_ao_desafio_e_falha_por_autorizacao` | Revogação real: `onboarding.md` §8.1. |
| 11 | Recuperação após nova autorização | `e2e/oauth-fal::test_recuperacao_depois_da_falha_transitoria`; `e2e/autorizar::test_reautorizacao_substitui_a_anterior` | A supressão de 6 h e o aviso de recuperação são os do gerenciador da feature 001. `onboarding.md` §8.2. |
| 12 | Serviço de autorização do Google fora do ar | `e2e/oauth-fal::test_servico_indisponivel_e_transitorio_e_preserva_o_arquivo` (503, 429, tempo esgotado, JSON inválido); `int/servico::test_classificacao_das_falhas_com_tentativa_unica`, `test_servico_inalcancavel_e_transitorio` | `onboarding.md` §8.3. |
| 13 | Troca de modo não duplica documentos | `e2e/oauth::test_troca_de_modo_nao_duplica_documentos` | `onboarding.md` §7. |
| 14 | Teste de acesso por caixa | `e2e/caixas::test_todas_as_caixas_confirmadas`, `test_uma_linha_por_desfecho_e_codigo_1`, `test_so_a_caixa_pedida`, `test_pasta_inexistente_e_falha`, `test_authenticate_recusado_e_servidor_fora_do_ar`, `test_cliente_recusado_pelo_google`, `test_indice_inexistente_sai_com_2`, `test_configuracao_invalida_e_nenhuma_caixa_valida_saem_com_2` | |
| 15 | Arquivo de autorização com permissão aberta | `uni/configuracao::test_permissao_aberta_da_autorizacao_gera_alerta`, `test_permissao_aberta_do_diretorio_gera_alerta`, `test_permissoes_corretas_nao_geram_alerta`, `test_diretorio_aberto_sem_caixa_oauth_nao_gera_alerta`; `e2e/oauth::test_permissao_aberta_da_autorizacao_vira_alerta_no_log` | `onboarding.md` §8.5. |
| 16 | Segredos fora dos logs | `e2e/oauth::test_nenhum_segredo_chega_ao_log`; `e2e/autorizar::test_sucesso_grava_a_autorizacao_e_sai_com_0`; `int/servico::test_log_traz_o_estado_e_o_erro_sem_nenhum_segredo`; `uni/configuracao::test_segredo_do_cliente_e_mascarado_e_fica_fora_do_repr`; `uni/arquivo::test_leitura_devolve_a_autorizacao_e_registra_o_segredo` | Em instalação real: `onboarding.md` §9 (ação T039). |

## Requisitos funcionais

| RF | Resumo | Testes | Verificação manual |
|----|--------|--------|--------------------|
| RF-01 | `AUTH_EMAIL<n>`: `senha` ou `oauth`, padrão `senha` | `uni/configuracao::test_auth_ausente_vale_senha_e_nada_muda`, `test_auth_aceita_maiusculas`, `test_auth_invalido_invalida_so_a_caixa`, `test_auth_orfa_gera_alerta`, `test_duplicidade_independe_do_modo` | `onboarding.md` §3 |
| RF-02 | Senha dispensada em `oauth`, exigida em `senha` | `uni/configuracao::test_caixa_oauth_dispensa_a_senha_e_e_valida_sem_autorizacao`, `test_senha_presente_em_caixa_oauth_e_ignorada_com_alerta`, `test_senha_ausente_invalida_so_a_caixa` | |
| RF-03 | Credenciais do cliente OAuth no `.env`, exigidas só com caixa em `oauth` | `uni/configuracao::test_credenciais_do_cliente_ausentes_invalidam_so_as_caixas_oauth`, `test_credenciais_do_cliente_sem_caixa_oauth_nao_geram_alerta`, `test_segredo_do_cliente_e_mascarado_e_fica_fora_do_repr` | |
| RF-04 | `autorizar-caixa <n>` grava a autorização com 600, sem imprimir segredo | `e2e/autorizar` (21 testes); `uni/arquivo` (23 testes); `uni/fluxo` (15 testes); `int/servico::test_troca_do_codigo_envia_o_verificador_e_o_retorno` | `onboarding.md` §5 |
| RF-05 | Autorização feita fora da VPS e copiada sem edição | `uni/arquivo::test_grava_com_600_em_diretorio_700_criado_sob_demanda` (nada no arquivo depende da máquina); `e2e/oauth` usa arquivos gravados fora do comando | `onboarding.md` §6 |
| RF-06 | Recusa quando a conta que consentiu difere de `EMAIL<n>` | `e2e/autorizar::test_conta_divergente_revoga_e_nada_grava`, `test_conta_divergente_com_revogacao_indisponivel`, `test_conta_nao_identificada`; `uni/fluxo::test_id_token_*` | `onboarding.md` §5 |
| RF-07 | `AUTHENTICATE XOAUTH2` com credencial temporária renovada a cada execução | `int/coleta::test_caixa_oauth_conecta_por_xoauth2_sem_login`, `test_so_comandos_de_leitura_e_body_peek`; `e2e/oauth::test_instalacao_mista_coleta_as_caixas_dos_dois_modos`, `test_credencial_temporaria_e_renovada_a_cada_execucao` | `onboarding.md` §7 |
| RF-08 | Falha de autorização só da caixa, com causa própria | `e2e/oauth-fal::test_autorizacao_ausente`, `test_invalid_grant_pede_nova_autorizacao_e_preserva_o_arquivo`, `test_autorizacao_de_outro_cliente_oauth`, `test_cliente_recusado_gera_um_aviso_so_e_pula_as_demais_caixas_oauth`, `test_authenticate_recusado_pelo_servidor_de_email`, `test_todas_as_caixas_em_falha_de_autorizacao_sai_com_codigo_2` | `onboarding.md` §8.1 e §8.4 |
| RF-09 | Serviço indisponível é falha transitória; a autorização não é descartada | `e2e/oauth-fal::test_servico_indisponivel_e_transitorio_e_preserva_o_arquivo`, `test_recuperacao_depois_da_falha_transitoria`; `int/servico::test_classificacao_das_falhas_com_tentativa_unica` | `onboarding.md` §8.3 |
| RF-10 | `verificar-config` mostra o modo e o estado da autorização, sem rede | `e2e/caixas::test_verificar_config_mostra_o_modo_e_o_estado_da_autorizacao`, `test_verificar_config_sem_oauth_fica_como_antes`; `uni/arquivo::test_estado_por_stat_sem_abrir_o_arquivo` | |
| RF-11 | `testar-caixa [<n>]`, uma tentativa por caixa | `e2e/caixas` (8 testes de `testar-caixa`) | `onboarding.md` §5 e §6 |
| RF-12 | Alerta de permissão aberta da autorização | `uni/configuracao::test_permissao_aberta_*`, `test_permissoes_corretas_nao_geram_alerta`; `e2e/oauth::test_permissao_aberta_da_autorizacao_vira_alerta_no_log` | `onboarding.md` §8.5 |
| RF-13 | Roteiro do Google Cloud e da operação no guia; `.env.example` | sem teste automatizado | `docs/instalacao-e-operacao.md` §16; leitura por terceiro na ação T039 |
| RF-14 | Comunicado ao titular | sem teste automatizado | `docs/instalacao-e-operacao.md` §16.2 |

## Invariantes vigiadas

| Invariante | Testes |
|------------|--------|
| A lista de comandos IMAP ganhou `AUTHENTICATE` e nada mais (W014, D-07) | `int/coleta::test_so_comandos_de_leitura_e_body_peek`, `test_caixa_oauth_conecta_por_xoauth2_sem_login`; `e2e/caixas::test_todas_as_caixas_confirmadas` |
| Uma tentativa de renovação por caixa e por execução (D-09) | `int/servico::test_classificacao_das_falhas_com_tentativa_unica`; `e2e/oauth-fal::test_servico_indisponivel_e_transitorio_e_preserva_o_arquivo` |
| Depois de `oauth:cliente`, nenhuma nova requisição na mesma execução (D-08) | `e2e/oauth-fal::test_cliente_recusado_gera_um_aviso_so_e_pula_as_demais_caixas_oauth`; `e2e/caixas::test_cliente_recusado_pelo_google` |
| O ciclo nunca escreve nem apaga o arquivo de autorização (RF-09) | `e2e/oauth::test_instalacao_mista_coleta_as_caixas_dos_dois_modos`; `e2e/oauth-fal` (comparação de bytes antes e depois) |
| A página de retorno não reflete parâmetros; `/favicon.ico` não consome o retorno | `e2e/autorizar::test_pagina_de_retorno_e_estatica_e_favicon_nao_consome_o_retorno` |
| Endereços do Google só mudam por injeção, nunca pelo `.env` (D-14) | `uni/fluxo::test_enderecos_padrao_sao_os_do_google`; não existe variável de ambiente lida para esse fim |

---

# Correções de bugs

> Fonte: `_reversa_bugs/email-nf-onedrive/bugs/<ID>/bug.md`, campos `traceability.reproduction_tests` e
> `regression_tests`. Estes testes não pertencem a nenhuma feature: nasceram de defeito observado em
> produção e ficam aqui para que uma correção futura não os desfaça sem querer.
> A spec efetiva de cada um está no adendo correspondente, em `_reversa_sdd/addenda/bug-<ID>-vNNN.md`.
> Estado na geração deste mapa: 393 testes, todos passando.

## `BUG-20260922-VBJD` · fornecedor recebe o nome da própria empresa

> Adendo: `bug-BUG-20260922-VBJD-v001.md` (veredito `spec-desatualizada`). Altera a leitura da
> RF-01 de `envio-onedrive` e acrescenta a ordem de fontes do fornecedor.

| Intenção | O que prova | Testes |
|----------|-------------|--------|
| reprodução | Remetente interno sem outra fonte não vira fornecedor | `uni/nomeacao::test_remetente_interno_sem_outra_fonte_fica_a_identificar` |
| reprodução | O PDF herda o emitente do XML da mesma mensagem | `uni/nomeacao::test_pdf_herda_o_emitente_do_xml_da_mesma_mensagem` |
| reprodução | O encaminhamento interno leva o remetente original | `uni/nomeacao::test_encaminhamento_interno_usa_o_remetente_original`; `e2e/arq::test_encaminhamento_interno_leva_o_fornecedor_real` |
| reprodução | A leitura MIME expõe o remetente original, anexado ou em linha | `uni/mime::test_encaminhada_como_anexo_expoe_o_remetente_original`, `test_encaminhada_em_linha_expoe_o_remetente_original` |
| reprodução | A coleta entrega ao envio as fontes do fornecedor | `int/coleta::test_coleta_entrega_ao_envio_as_fontes_do_fornecedor` |
| regressão | Remetente externo segue inalterado | `uni/nomeacao::test_remetente_externo_sem_outra_fonte_nao_muda`, `test_encaminhamento_por_externo_usa_o_remetente_original` |
| regressão | Provedor genérico não é domínio interno | `uni/nomeacao::test_remetente_de_provedor_generico_nao_e_interno`; `uni/configuracao::test_dominios_internos_sao_os_das_caixas_sem_os_genericos` |
| regressão | Precedência entre as fontes | `uni/nomeacao::test_emitente_do_proprio_xml_vence_o_da_mensagem`, `test_emitente_da_mensagem_vence_o_remetente_original`, `test_remetente_original_interno_e_pulado`, `test_dominio_interno_comparado_sem_diferenca_de_caixa`, `test_pdf_de_remetente_externo_tambem_herda_o_emitente_do_xml` |
| regressão | Linha `De:` sem endereço não conta como remetente | `uni/mime::test_mensagem_direta_nao_tem_remetente_encaminhado`, `test_remetentes_citados_no_corpo` |

## `BUG-20260922-RWDA` · resumo com `0 enviados` após interrupção

> Adendo: `bug-BUG-20260922-RWDA-v001.md` (veredito `spec-gap`). Acrescenta a RF-14 (limite de 20 min
> e interrupção), relê a RF-11 de `execucao-monitoramento` e cria o caso EC-RWDA-1.

| Intenção | O que prova | Testes |
|----------|-------------|--------|
| reprodução | O resumo da execução interrompida conta os envios já confirmados, e o número bate com o log, o destino e o registro | `e2e/fal::test_interrupcao_por_tempo_conta_os_envios_ja_confirmados` |
| regressão | A interrupção mantém o código de saída 2 e o aviso `execucao:tempo` | `e2e/fal::test_interrupcao_por_tempo_preserva_o_codigo_e_o_aviso` |
| regressão | Falha de anexo ocorrida antes da interrupção também entra no resumo | `e2e/fal::test_falha_de_anexo_antes_da_interrupcao_entra_no_resumo` |
| regressão | `enviar_anexos` preenche o acumulador de quem chama, e sem o parâmetro segue como antes | `int/envio::test_resultado_de_quem_chama_e_preenchido_a_cada_envio` |
| regressão | A simulação diz no resumo quantos anexos avaliou | `e2e/arq::test_simulacao_diz_no_resumo_quantos_anexos_avaliou` |

O dublê `_RcloneInterrompido`, em `e2e/fal`, estende o Rclone real e levanta `TempoEsgotado` na
N-ésima cópia: a mesma exceção que `limite_duracao` levanta a partir do SIGALRM, no mesmo ponto do
laço de envio. `signal.alarm` só aceita segundos inteiros, e um teste por relógio dependeria de o
alarme cair no envio, e não na coleta.

# Feature `003-destino-por-vencimento`

> Adendo: `_reversa_sdd/addenda/003-destino-por-vencimento.md` (RF-15). Fixtures sintéticas em
> `tests/conftest.py`: `pdf_com_texto` e `nfe_com_vencimentos`.

| O que prova | Testes |
|-------------|--------|
| XML: primeiro `dVenc` entre as parcelas; sem cobrança, sem vencimento | `uni/vencimento::test_nfe_devolve_o_primeiro_vencimento_das_parcelas`, `test_nfe_sem_cobranca_nao_tem_vencimento` |
| Fator de vencimento nos dois ciclos Febraban e fator zero | `uni/vencimento::test_fator_de_vencimento_escolhe_o_ciclo_mais_proximo`, `test_fator_zero_e_boleto_sem_vencimento`, `test_fator_do_ciclo_antigo_vale_para_documento_antigo` |
| Linha digitável com e sem separadores; dígito verificador errado não conta | `uni/vencimento::test_boleto_pela_linha_digitavel`, `test_linha_digitavel_sem_separadores`, `test_sequencia_com_digito_verificador_errado_nao_e_linha_digitavel` |
| Data no texto, com emissão ao lado e data anterior ao recebimento descartadas | `uni/vencimento::test_vencimento_no_texto` |
| Ordem das fontes para PDF, XML e imagem | `uni/vencimento::test_ordem_das_fontes_para_pdf`, `test_ordem_das_fontes_para_xml`, `test_imagem_so_tem_o_vencimento_da_mensagem` |
| Vencimento da mensagem: XML irmão antes de boleto irmão | `uni/vencimento::test_vencimento_da_mensagem_prefere_o_xml_e_cai_no_boleto`, `test_coleta_toma_o_vencimento_do_xml_irmao` |
| Caminho `NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>` e raiz sem vencimento | `uni/vencimento::test_pasta_por_vencimento`, `test_sem_vencimento_fica_na_raiz_do_destino` |
| O envio grava na subpasta, parcela só no primeiro vencimento, DANFE herda e boleto usa o próprio | `int/envio::test_nota_em_xml_vai_para_a_pasta_do_vencimento`, `test_nota_parcelada_vai_so_para_o_primeiro_vencimento`, `test_danfe_herda_o_vencimento_do_xml_da_mensagem_e_boleto_usa_o_proprio` |
| Sem vencimento vai à raiz; subpasta ausente falha sem ser criada | `int/envio::test_pdf_sem_vencimento_fica_na_raiz`, `test_pasta_do_vencimento_ausente_nao_e_criada` |

# Adendo `004-desempenho-coleta-envio`

| O que prova | Testes |
|-------------|--------|
| Mensagens resolvidas: anexos terminais ou só ocorrência, sem nenhum pendente | `uni/registro::test_mensagens_resolvidas` |
| A coleta lê o `Message-ID` e não baixa de novo a mensagem resolvida; a sem `Message-ID` e a com pendente seguem sendo baixadas | `int/coleta::test_mensagem_resolvida_nao_e_baixada_de_novo`, `test_mensagem_com_pendente_continua_sendo_baixada`, `test_so_comandos_de_leitura_e_body_peek` |
| O envio usa até 4 threads, e o mesmo nome (também só na caixa) recebe sufixos sem colisão | `int/envio::test_envios_correm_em_paralelo`, `test_mesmo_nome_em_paralelo_recebe_sufixos_sem_colisao`, `test_nomes_que_so_diferem_na_caixa_vao_na_mesma_fila` |
| Interrupção com envios em curso: resumo igual ao registro, e a execução seguinte não duplica | `e2e/fal::test_interrupcao_com_envios_em_paralelo_nao_duplica_na_execucao_seguinte` |

O dublê `_RcloneInterrompido` passou a disparar um SIGALRM real, que `limite_duracao` converte em
`TempoEsgotado` na thread principal, e os três testes do `BUG-20260922-RWDA` rodam com um envio por
vez (`Dependencias.envios_simultaneos = 1`), porque "a N-ésima cópia" só é determinística em série.

# Adendo `005-timeout-rclone`

| O que prova | Testes |
|-------------|--------|
| O limite padrão de 300 s chega ao processo do Rclone | `uni/rclone::test_limite_padrao_de_300_s_chega_ao_processo` |
| Chamada que estoura o limite vira `ErroRclone` de causa `timeout` | `uni/rclone::test_chamada_que_estoura_o_limite_vira_falha_de_tempo` |
