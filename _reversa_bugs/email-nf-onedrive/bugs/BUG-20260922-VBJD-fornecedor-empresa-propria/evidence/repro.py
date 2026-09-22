from pathlib import Path
from email_nf_onedrive.coleta.mime import analisar_mensagem
from email_nf_onedrive.coleta.classificacao import classificar, NFE_XML
from email_nf_onedrive.envio.nomeacao import DadosNome, nome_destino

D = Path("tests/dados")
xml = (D / "nfe_proc.xml").read_bytes()
casos = {
  "1 encaminhamento interno, PDF sem XML": DadosNome(empresa="ACME", remetente="colega@empresa.example",
      nome_original="boleto.pdf", assunto="Fwd: Boleto", classe="palavra-chave"),
  "2a mesma mensagem: XML": DadosNome(empresa="ACME", remetente="colega@empresa.example",
      nome_original="nfe.xml", assunto="Fwd: NF", classe=NFE_XML, conteudo=xml),
  "2b mesma mensagem: PDF irmão": DadosNome(empresa="ACME", remetente="colega@empresa.example",
      nome_original="danfe.pdf", assunto="Fwd: NF", classe="palavra-chave"),
  "3 remetente externo": DadosNome(empresa="ACME", remetente="cobranca@fornecedor.com.br",
      nome_original="boleto.pdf", assunto="Boleto", classe="palavra-chave"),
}
for k, v in casos.items():
    print(f"{k:40s} -> {nome_destino(v)}")
m = analisar_mensagem((D / "encaminhada.eml").read_bytes())
print("encaminhada.eml (rfc822 anexo): remetente usado =", m.remetente,
      "->", nome_destino(DadosNome(empresa="ACME", remetente=m.remetente, nome_original=m.anexos[0].nome,
                                   assunto=m.assunto, classe="palavra-chave")))
