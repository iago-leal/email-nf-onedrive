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
| RF-10 | Nome padronizado, saneado, até 200 caracteres | `uni/nomeacao` (12 testes) | Convenção provisória até a L-03 (`onboarding.md` §3) |
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
