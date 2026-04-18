from datetime import datetime
import logging

def parse_detalhes(json_response, lote_id_param=None):
    """
    Consome o retorno do LoadDetalhes e retorna uma lista de FaturamentoLotes persistíveis.
    """
    items = []
    
    if not isinstance(json_response, (dict, list)):
        logging.error(f"parse_detalhes: Unexpected JSON type ({type(json_response)}): {json_response}")
        return items

    if isinstance(json_response, dict):
        data_list = json_response.get("Detalhes") or json_response.get("Data") or json_response.get("Itens") or []
        if not data_list:
            for k, v in json_response.items():
                if isinstance(v, list) and len(v) > 0:
                    data_list = v
                    break
    else:
        data_list = json_response

    if isinstance(data_list, dict) and "DataList" in data_list:
        data_list = data_list["DataList"]
    elif not isinstance(data_list, list):
         data_list = []

    lote_id = lote_id_param or (json_response.get("loteId", json_response.get("LoteId")) if isinstance(json_response, dict) else None)

    for item in data_list:
        if not isinstance(item, dict):
            continue
        try:
            # Transform date (handles both dd/mm/yyyy and yyyy-mm-ddThh:mm:ss format)
            dt_str = item.get("DataRealizacaoProcedimento") or item.get("DataRealizacao")
            data_realizacao = None
            if dt_str:
                if "T" in dt_str:
                    data_realizacao = datetime.strptime(dt_str.split("T")[0], "%Y-%m-%d").date()
                else:
                    data_realizacao = datetime.strptime(dt_str, "%d/%m/%Y").date()

            # Transform value
            val_str = item.get("ValorProcedimento")
            valor_proc = float(val_str) if val_str else 0.0

            parsed_item = {
                "loteId": lote_id,
                "detalheId": item.get("Id"),
                "CodigoBeneficiario": item.get("CodigoBeneficiario"),
                "dataRealizacao": data_realizacao,
                "Guia": item.get("Guia"),
                "StatusConferencia": item.get("StatusConferencia"),
                "ValorProcedimento": valor_proc
            }
            items.append(parsed_item)
        except Exception as e:
            logging.error(f"Error parsing item {item}: {e}")

    return items

def extract_total_pages(json_response):
    """
    Retorna o número total de páginas da consulta.
    """
    if isinstance(json_response, dict):
        return int(json_response.get("NumberOfPages", "\n0\n").strip() or 0) if isinstance(json_response.get("NumberOfPages"), str) else int(json_response.get("NumberOfPages") or 0)
    return 1

