# Política de privacidade do email-nf-onedrive

Vigente desde 22 de setembro de 2026.

O `email-nf-onedrive` é uma ferramenta de uso interno, instalada num servidor da empresa contratante, que arquiva automaticamente as notas fiscais e os boletos recebidos nas caixas de e-mail financeiras dessa empresa. Não é um serviço oferecido ao público, e cada instalação atende apenas às caixas configuradas pelo seu operador.

## Quais dados são acessados

Com a autorização do titular de cada caixa, concedida pelo Google (OAuth 2.0), a ferramenta lê as mensagens da pasta configurada, a partir de uma data inicial, e extrai os anexos PDF e XML. Da conta Google, usa apenas o endereço de e-mail, para confirmar que a autorização foi dada pela caixa correta.

Embora o Google só ofereça, para esse tipo de acesso, uma permissão ampla, que inclui enviar e excluir mensagens, a ferramenta **apenas lê**: não envia, não apaga, não move nem marca mensagens como lidas.

## Para que os dados são usados

Exclusivamente para identificar notas fiscais e boletos e copiá-los para a pasta da empresa no OneDrive for Business, com nome padronizado. Nenhum dado é usado para publicidade, vendido, compartilhado com terceiros ou usado para treinar modelos de inteligência artificial.

## O que fica guardado

- Os documentos arquivados, na pasta da própria empresa no OneDrive.
- Um registro local dos anexos já processados (endereço da caixa, identificador da mensagem e resumo criptográfico do anexo), para não copiar o mesmo documento duas vezes.
- Registros de execução, sem senhas nem credenciais.
- A autorização concedida pelo titular, num arquivo protegido no servidor da empresa, acessível apenas à própria ferramenta.

Os dados ficam no servidor da empresa contratante e no OneDrive dela. O desenvolvedor não mantém cópia.

## Como revogar

O titular pode retirar o acesso a qualquer momento em <https://myaccount.google.com/permissions>, removendo o `email-nf-onedrive`. A partir daí, a ferramenta deixa de ler a caixa.

## Uso limitado dos dados do Google

O uso e a transferência, para qualquer outro aplicativo, de informações recebidas das APIs do Google seguem a [Política de Dados do Usuário dos Serviços de API do Google](https://developers.google.com/terms/api-services-user-data-policy), incluindo os requisitos de uso limitado.

## Contato

Dúvidas sobre esta política ou sobre o tratamento de dados, inclusive para o exercício dos direitos previstos na Lei Geral de Proteção de Dados (Lei nº 13.709/2018): iagoleal@medicinaleal.com.
