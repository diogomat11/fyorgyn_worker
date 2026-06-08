/* Minification failed. Returning unminified contents.
(5821,67): run-time error JS1004: Expected ';'
(5821,77-78): run-time error JS1010: Expected identifier: (
(5824,35): run-time error JS1004: Expected ';'
(5833,31): run-time error JS1004: Expected ';'
 */
//REPOSITORIES
var get = function extender(url, param, pAsync) {
    var async = true;

    if (!IsUndefinedOrNullOrEmpty(pAsync))
        async = pAsync === true ? true : false;

    return $.ajax({
        type: "GET",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        data: { param: param },
        cache: false,
        async: async
    });
};
var post = function extender(url, param, pAsync) {
    var async = true;

    if (!IsUndefinedOrNullOrEmpty(pAsync))
        async = pAsync === true ? true : false;
    return $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        data: { param: param },
        cache: false,
        async: async
    });
};

var getWithoutParam = function extender(url, async) {
    return $.ajax({
        type: "GET",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        cache: false,
        async: async === true ? true : false
    });
};
var postData = function extender(url, data, async) {
    return $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        data: JSON.stringify(data),
        cache: false,
        async: async === true ? true : false
    });
};

var putData = function extender(url, data, async) {
    return $.ajax({
        type: "PUT",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        data: JSON.stringify(data),
        cache: false,
        async: async === true ? true : false
    });
};

var postDataNotTimeOut = function extender(url, data, async) {
    return $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json",
        url: basePath.concat(url),
        timeout: 2 * 60 * 60 * 1000,
        data: JSON.stringify(data),
        cache: false,
        async: async === true ? true : false
    });
};

var base64ToArrayBuffer = function extender(base64) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
};

function ExecutanteRepository() {
    var self = this;

    self.getExecutante = function (id, nome) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/GetExecutanteByCodigo", //o controller nao influencia pois o metodo esta no controller base
            data: {
                idExecutante: id,
                nomeExecutante: nome
            },
            cache: false,
        });
    };
    self.getExecutanteModel = function (id, nome) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/GetExecutanteModelByCodigo",  //o controller nao influencia pois o metodo esta no controller base
            data: {
                idExecutante: id,
                nomeExecutante: nome
            },
            cache: false,
        });
    };
    self.searchExecutante = function (value, idContratado) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/SearchProfissionaisExecutantes",
            data: {
                value: value,
                idContratado: idContratado
            },
            cache: false,
        });
    };
    self.searchExecutanteModel = function (value, idContratado, ehPrestadorOdonto) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/SearchProfissionaisExecutantesModel",
            data: {
                value: value,
                idContratado: idContratado,
                ehPrestadorOdonto: ehPrestadorOdonto,
            },
            cache: false,
        });
    };
}
function GuiaOdontologicaRepository() {
    var self = this;

    self.searchDente = function (param) {
        return get("GuiasTISS/GuiaOdontologica/SearchDente", cryptography(param));
    };
    self.searchFace = function (param) {
        return get("GuiasTISS/GuiaOdontologica/SearchFace", cryptography(param));
    };
    self.searchRegiao = function (param) {
        return get("GuiasTISS/GuiaOdontologica/SearchRegiao", cryptography(param));
    };
    self.searchServicoOdontologico = function (codigoPrestador, tipoPrestador, textoPesquisa, codSeg) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/SearchServicoOdontologico",
            data: {
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                textoPesquisa: textoPesquisa,
                codSeg: codSeg
            },
            cache: false
        });
    };
    self.searchServicoOdontologicoPrestadorNaoObrigatorio = function (codigoPrestador, tipoPrestador, textoPesquisa, pesquisarSemPrestador) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/SearchServicoOdontologicoRelatorio",
            data: {
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                textoPesquisa: textoPesquisa,
                pesquisarSemPrestador: pesquisarSemPrestador
            },
            cache: false
        });
    };
    self.getServicoOdontologico = function (codigoPrestador, tipoPrestador, codigoTabela, codigoServico, codigoBeneficiario) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/GetInformacoesProcedimentoOdontologico",
            data: {
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                codigoTabela: codigoTabela,
                codigoServico: codigoServico,
                codigoBeneficiario: codigoBeneficiario
            },
            cache: false
        })
    };
    self.getServicoOdontologicoPrestadorNaoObrigatorio = function (codigoPrestador, tipoPrestador, codigoTabela, codigoServico, codigoBeneficiario) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/GetInformacoesProcedimentoOdontologicoRelatorio",
            data: {
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                codigoTabela: codigoTabela,
                codigoServico: codigoServico,
                codigoBeneficiario: codigoBeneficiario
            },
            cache: false
        })
    };
    self.getFacesPossiveisByDente = function (dente, listaFaces) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/GetFacesPossiveisDente",
            data: {
                dente: dente,
            },
            cache: false
        })
    };
    self.saveGuiaOdontologica = function (viewModel) {
        return $.ajax({
            type: "POST",
            contentType: 'application/json',
            url: basePath + "GuiasTISS/GuiaOdontologica/SalvarGuiaOdontologica",
            data: JSON.stringify(viewModel),
            cache: false
        });
    };
    self.imprimirGuiaOdontologica = function (viewModel) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiasTISS/GuiaOdontologica/ImprimirGuiaOdontologica",
            data: { data: JSON.stringify(viewModel) },
            cache: false

        });
    };
    self.faceValidaInFacesPossiveis = function (face, facesPossiveis) {
        var result = true;
        var ind = 0;
        for (ind = 0; ind < face.Id.length; ind++) {
            if (facesPossiveis.indexOf(face.Id[ind]) == -1) {
                result = false;
                break;
            }
        }
        return result;
    };
    self.ajustaFacesPossiveis = function (facesPossiveis, todasFaces) {
        var retorno = new Array();
        var index = 0;
        for (index = 0; index < todasFaces.length; index++) {
            if (self.faceValidaInFacesPossiveis(todasFaces[index], facesPossiveis)) {
                retorno.push(todasFaces[index]);
            }
        }
        return retorno;
    };
    self.getAllMonthsByBeneficiarioIdGroupedByDate = function (beneficiarioId, prestadorId) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "GuiasTISS/GuiaOdontologica/GetAllMonthsByBeneficiarioIdGroupedByDate",
            data: {
                beneficiarioId: beneficiarioId,
                prestadorId: prestadorId
            },
            cache: false
        })
    };
    self.getAllImagesByBeneficiarioIdGroupedByDate = function (beneficiarioId, prestadorId, mes) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "GuiasTISS/GuiaOdontologica/GetAllByBeneficiarioIdGroupedByDate",
            data: {
                beneficiarioId: beneficiarioId,
                prestadorId: prestadorId,
                mes: mes
            },
            cache: true
        })
    };
}
function ProcedimentoRepository() {
    var self = this;

    self.getProcedimentoPadrao = function (codigoPrestador, tipoPrestador) {
        return $.ajax({
            type: "POST",
            url: basePath + "Procedimento/GetProcedimentoPadraoByPrestador",
            data: { tipoEnt: tipoPrestador, codEnt: codigoPrestador },
            cache: false,
        });
    };
    self.getValorProcedimento = function (codigoTabela, codigoProcedimento, tipoServico, codigoSegurado, codigoContratado, cbos, valorManual, pcmso, codEspecialidadeFacplan) {
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/GetValorProcedimento",
            data: {
                codTabela: codigoTabela,
                codProcedimento: codigoProcedimento,
                codSeg: codigoSegurado,
                tipoEnt: codigoContratado.split('-')[1],
                codEnt: codigoContratado.split('-')[0],
                tipoServ: tipoServico,
                codCBOS: cbos,
                valorManual: valorManual,
                pcmso: pcmso,
                codEspecialidadeFacplan: codEspecialidadeFacplan
            },
            cache: false,
        });
    };
    self.pesquisarProcedimentos = function (texto) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/PesquisarProcedimento"),
            data: {
                text: texto
            }
        });
    };
    self.getDetalhesProcedimentoHierarquizado = function (param) {
        return get("Procedimento/SearchDetalhesProcedimentoHierarquizado", cryptography(param));
    };
    self.ehConsultaProntoSocorroPadrao = function (param) {
        return get("Guias/EhConsultaProntoSocorroPadrao", cryptography(param));
    };
    self.getTiposDeAnexoDeProcedimento = function (param) {
        return get("Procedimento/GetTiposDeAnexoDeProcedimento", cryptography(param));
    };
    self.getProcedimentosToReapresentacao = function (param) {
        return get("ReapresentacaoGuia/GetProcedimentosToReapresentacao", cryptography(param));
    };
    self.search = function (tabela, codigoPrestador, criterio, somenteRadioterapicos, tipoGuia) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/Localizar"),
            data: {
                criterio: criterio,
                tabela: tabela,
                codigoPrestador: codigoPrestador,
                somenteRadioterapicos: somenteRadioterapicos,
                tipoGuia: tipoGuia
            },
            cache: false,
        });
    };
    self.searchFull = function (param) {
        return get("Procedimento/LocalizarProcedimentoFull", cryptography(param));
    };
    self.searchAnonymous = function (codigoPrestador, criterio, somenteRadioterapicos, tipoGuia) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/LocalizarAnonymous"),
            data: {
                criterio: criterio,
                codigoPrestador: codigoPrestador,
                somenteRadioterapicos: somenteRadioterapicos,
                tipoGuia: tipoGuia
            },
            cache: false,
        });
    };
    self.searchFarmacia = function (criterio, somenteGenerico, beneficiario, idItemReceita) {//tabela, codigoPrestador, criterio, somenteRadioterapicos, tipoGuia
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/LocalizarFarmacia"),
            data: {
                criterio: criterio,
                somenteGenerico: somenteGenerico,
                beneficiario: beneficiario,
                idItemReceita: idItemReceita,
            },
            cache: false,
        });//, tabela: tabela, codigoPrestador: codigoPrestador, somenteRadioterapicos: somenteRadioterapicos, tipoGuia: tipoGuia 
    };
    self.searchPedidoExame = function (criterio, beneficiario, codigoPrestador) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/LocalizarPedidoDeExame"),
            data: {
                criterio: criterio,
                beneficiario: beneficiario,
                codigoPrestador: codigoPrestador
            },
            cache: false,
        });
    };
    self.searchById = function (tabela, codigoPrestador, criterio, somenteRadioterapicos, tipoGuia, codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/LocalizarPorCodigo"),
            data: {
                criterio: criterio,
                tabela: tabela,
                codigoPrestador: codigoPrestador,
                somenteRadioterapicos: somenteRadioterapicos,
                tipoGuia: tipoGuia,
                codigoBeneficiario: codigoBeneficiario
            },
            cache: false,
        });
    };
    self.searchLote = function (tipoGuia, codigoPrestador, criterio, codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Procedimento/LocalizarLote"),
            data: {
                tipoGuia: tipoGuia,
                codigoPrestador: codigoPrestador,
                criterio: criterio,
                codigoBeneficiario: codigoBeneficiario
            },
            cache: false,
        });
    };
    self.searchLoteByWebService = function (carteiraBeneficiario, contratadoExecutante, urlWebService, usuarioWebService, senhaWebService) {
        return $.ajax({
            type: "GET",
            url: urlWebService + "/getByBeneficiario",
            data: {
                carteiraBeneficiario: carteiraBeneficiario,
                codigoPrestador: contratadoExecutante.substring(0, contratadoExecutante.indexOf("-")),
                tipoPrestador: contratadoExecutante.substring(contratadoExecutante.indexOf("-") + 1, contratadoExecutante.length)
            },
            dataType: "json",
            headers: { "Authorization": "Basic " + btoa(usuarioWebService + ":" + senhaWebService) }
        });
    };
    self.procedimentosInseridosWebService = function (numGuiaPrestador, procedimentos, urlWebService, usuarioWebService, senhaWebService) {
        var procs = [];

        ko.utils.arrayForEach(procedimentos, function (p) {
            procs.push({
                codigo: p.codigo,
                quantidade: p.quantidade
            })

        });

        return $.ajax({
            type: "POST",
            url: urlWebService + "/procedimentosInseridos",
            data: JSON.stringify({ procedimentos: procs, guiaPrestador: numGuiaPrestador }),
            cache: false,
            contentType: 'application/json',
            headers: { "Authorization": "Basic " + btoa(usuarioWebService + ":" + senhaWebService) }
        });
    };
    self.validarProcedimentosPrestadorParaReapresentacao = function (solicitacao) {
        return $.ajax({
            type: "POST",
            url: basePath + "ReapresentacaoGuia/ValidarProcedimentosPrestador",
            data: solicitacao,
            contentType: 'application/json',
            dataType: 'json'
        });
    };
}
function EspecialidadeMedicaRepository() {
    var self = this;

    self.get = function (param) {
        return get("especialidademedica/get", cryptography(param));
    };
    self.getEspecialidade = function (codigoPrestador, tipoPrestador) {
        if (0 == tipoPrestador) { // Médico
            var method = "GetObjetosEspecialidadesMedicasByCodMed";
            var params = { "idMedico": codigoPrestador };
        }
        else {
            var method = "GetObjetosEspecialidadesMedicasByCodHosp";
            var params = { "idHosp": codigoPrestador };
        }
        return $.ajax({
            type: "POST",
            url: basePath + "GuiaConsulta/" + method,
            data: params,
            cache: false,
        });
    };
    self.getApi = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/EspecialidadeMedica/Get",
            data: filtro,
            dataType: "json",
        });
    };
    self.search = function (texto, codPrestador) {
        return $.ajax({
            type: "POST",
            url: basePath + "EspecialidadeMedica/SearchPrestador",
            data: { "texto": texto, "codPrestador": codPrestador },
            dataType: "json",
        });
    };
}
function LoteFaturamentoRepository() {
    var self = this;

    self.getLotes = function (page, quantidadePorPagina, codigoPrestador, login) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadLotes",
            data: { page: page, quantidadePorPagina: quantidadePorPagina, codigoPrestador: codigoPrestador, login: login },
            cache: false,
        });
    };
    self.gerarLote = function (dataFinal, codigoPrestador) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/GerarLote",
            data: { dataFinal: dataFinal, codigoPrestador: codigoPrestador },
            cache: false,
            async: true
        });
    };
    self.cancelarLote = function (loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/CancelarLote",
            data: { loteId: loteId },
            cache: false,
        });
    };
    self.enviarLote = function (loteId, aceitarItensNaoConferidos) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/EnviarLote",
            data: { loteId: loteId, aceitarItensNaoConferidos: aceitarItensNaoConferidos },
            cache: false,
        });
    };
    self.getDetalhes = function (filtro) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadDetalhes",
            data: JSON.stringify(filtro),
            cache: false,
            contentType: 'application/json;'
        });
    };
    self.imprimirDetalhes = function (filtro, ordenacao) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/ImprimirDetalhes",
            data: JSON.stringify({ filtro: filtro, ordenacao: ordenacao }),
            cache: false,
            contentType: 'application/json;'
        });
    };
    self.imprimirSintetico = function (loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/ImprimirSintetico",
            data: { loteId: loteId },
            cache: false
        });
    };
    self.getTaxas = function (detalheId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadTaxas",
            data: { detalheId: detalheId },
            cache: false,
        });
    };
    self.getMatMeds = function (detalheId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadMatMeds",
            data: { detalheId: detalheId },
            cache: false,
        });
    };
    self.getHonorarios = function (detalheId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadHonorarios",
            data: { detalheId: detalheId },
            cache: false,
        });
    };
    self.salvarDetalheProcedimento = function (detalheProcedimento) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/SalvarDetalheProcedimento",
            data: JSON.stringify(detalheProcedimento),
            cache: false,
            contentType: 'application/json;',
        });
    };
    self.removerDetalheProcedimento = function (detalheProcedimento) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/RemoverDetalheProcedimento",
            data: JSON.stringify(detalheProcedimento),
            cache: false,
            contentType: 'application/json;',
        });
    };
    self.modificarDetalheProcedimento = function (detalheId, status, dataRealizacao, valorOutrasDespesas, atualizarValorProcedimento, valorProcedimento) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/ModificarDetalhe",
            data: { detalheId: detalheId, status: status, dataRealizacao: dataRealizacao, valorOutrasDespesas: valorOutrasDespesas, atualizarValorProcedimento: atualizarValorProcedimento, valorProcedimento: valorProcedimento },
            cache: false,
        });
    };
    self.atualizarNaoConfirmado = function (detalheId) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/AtualizarDetalheNaoConfirmado ",
            data: { detalheId: detalheId },
            cache: false,
        });
    };
    self.modificarStatusGuia = function (loteId, guia, status) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/ModificarStatusGuia",
            data: { loteId: loteId, guia: guia, status: status },
            cache: false,
        });
    };
    self.loadDetalhesCirurgia = function (CodCirurgia) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/LoadDetalhesCirurgia",
            data: { CodCirurgia: CodCirurgia },
            cache: false,
        });
    };
    self.modificarStatusLote = function (loteId, status) {
        return $.ajax({
            type: "POST",
            url: basePath + "FaturamentoAtendimentos/ModificarStatusLote",
            data: { loteId: loteId, status: status },
            cache: false,
        });
    };
    self.findProcedimentoRealizado = function (localAtendimento, codigoBeneficiario, codigoProcedimento, guia, senha) {
        return $.ajax({
            type: "POST",
            url: basePath + "/FaturamentoAtendimentos/FindProcedimentoRealizado",
            data: { localAtendimento: localAtendimento, codigoBeneficiario: codigoBeneficiario, codigoProcedimento: codigoProcedimento, guia: guia, senha: senha },
            cache: false,
        });
    };
    self.findProcedimentoSenhaGuia = function (guia, senha, loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "/FaturamentoAtendimentos/FindProcedimentosSenhaGuia",
            data: { guia: guia, senha: senha, loteId: loteId },
            cache: false,
        });
    };
    self.addProcedimentoLote = function (procedimento, loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "/FaturamentoAtendimentos/AdicionaProcedimentoLote",
            data: JSON.stringify({ loteId: loteId, procedimento: procedimento }),
            cache: false,
            contentType: 'application/json;',
        });
    };
    self.checkImpressaoLoteStatus = function (loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "/FaturamentoAtendimentos/CheckImpressaoLoteStatus",
            data: JSON.stringify({ loteId: loteId }),
            cache: false,
            contentType: 'application/json;',
        })
    };
    self.existemItensConferidos = function (param) {
        return get("FaturamentoAtendimentos/ExistemItensConferidos", cryptography(param));
    };
    self.obrigaEnvioAnexo = function (param) {
        return get("FaturamentoAtendimentos/ValidarObrigatoriedadeEnvioAnexo");
    };
    self.getProgresso = function (loteId) {
        var url = basePath + "/FaturamentoAtendimentos/getProgresso";
        return $.ajax({
            type: "GET",
            url: url,
            cache: false,
            async: true
        })
    };
    self.enviarArquivosffp = function (protocoloId, arquivos, response) {
        var url = basePath + "FaturamentoAtendimentos/EnviarArquivosAnexos";
        var data = {
            protocoloId: protocoloId,
            files: arquivos
        };

        $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false,
            success: function (data) {
                if (response) {
                    response(data);
                }
            }
        });
    }
    self.carregarAnexos = function (param) {
        return get("FaturamentoAtendimentos/CarregarAnexos", cryptography(param));
    };
    self.gerarGuiaOutrasDespesas = function (param) {
        var url = basePath.concat("FaturamentoAtendimentos/GerarGuiaOutrasDespesas?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.relatorioGuiaConsulta = function (param) {
        var url = basePath.concat("Relatorios/NovaViewRelatorioGuiaConsulta?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.gerarGuiaHonorario = function (param) {
        var url = basePath.concat("FaturamentoAtendimentos/GerarGuiaHonorario?param=", cryptography(param));
        window.open(url, "_blank");
    };
}
function TaxaRepository() {
    var self = this;

    self.search = function (criteria, dataRealizacao, prestador, codigoBeneficiario) {
        return $.ajax({
            type: "POST",
            url: basePath + "Taxa/Search",
            data: { criteria: criteria, dataRealizacao: dataRealizacao, prestador: prestador, codigoBeneficiario: codigoBeneficiario },
            cache: false,
        });
    };
    self.calcularValor = function (id, codigoPrestador, codigoSegurado) {
        return $.ajax({
            type: "POST",
            url: basePath + "Taxa/CalcularValor",
            data: { id: id, codigoPrestador: codigoPrestador, codigoSegurado: codigoSegurado },
            cache: false,
            async: false
        });
    };
}
function MaterialMedicamentoRepository() {
    var self = this;

    self.search = function (criteria, dataRealizacao, codigoServico, tipoServico, codSegurado, codigoPrestador) {
        return $.ajax({
            type: "POST",
            url: basePath + "MaterialMedicamento/Search",
            data: { criteria: criteria, dataRealizacao: dataRealizacao, codigoServico: codigoServico, tipoServico: tipoServico, codSegurado: codSegurado, codigoPrestador: codigoPrestador },
            cache: false
        });
    };
    self.calcularValor = function (id, codigoPrestador, codigoSegurado) {
        return $.ajax({
            type: "POST",
            url: basePath + "MaterialMedicamento/CalcularValor",
            data: { id: id, codigoPrestador: codigoPrestador, codSegurado: codigoSegurado },
            cache: false,
            async: false
        });
    };
}
function IRRepository() {
    var self = this;

    self.gerarRelatorio = function (ano, codPrestador, considerarOutrosCadastrosBatimentoDIRF) {
        return $.ajax({
            type: "POST",
            url: basePath + "IR/GerarRelatorioAnualIR",
            data: { ano: ano.year(), codPrestador: codPrestador, considerarOutrosCadastrosBatimentoDIRF: considerarOutrosCadastrosBatimentoDIRF },
            cache: false,
        });
    };
    self.print = function (ano, codPrestador, tipoRelatorio, considerarOutrosCadastrosBatimentoDIRF) {
        return $.ajax({
            type: "GET",
            url: basePath + "IR/RelatorioAnualIRPdf",
            data: { ano: ano, codPrestador: codPrestador, tipoRelatorio: tipoRelatorio, considerarOutrosCadastrosBatimentoDIRF: considerarOutrosCadastrosBatimentoDIRF },
            cache: false,
        });
    };
    self.gerarRelatorioBeneficiario = function (ano, codBeneficiario, considerarOutrosCadastrosBatimentoDIRF) {
        return $.ajax({
            type: "POST",
            url: basePath + "IRBeneficiario/RelatorioAnualIRPdf",
            data: { ano: ano.year(), codBeneficiario: codBeneficiario, considerarOutrosCadastrosBatimentoDIRF: considerarOutrosCadastrosBatimentoDIRF },
            cache: false,
        });
    };
    self.getIRFamilias = function (param) {
        return get("IRBeneficiario/FamiliaDados", cryptography(param));
    };
}
function BiometriaRepository() {
    var self = this;

    self.utilizaApplet = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "Biometria/UtilizaApplet",
            cache: false,
            async: false,
        });
    };
    self.utilizaNovaBiometria = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "Biometria/UtilizaNovaBiometria",
            cache: false,
            async: false,
        });
    };
}
function DemonstrativoPagamentoRepository() {
    var self = this;

    self.pesquisar = function (codigoPrestador, dataPagamento, competencia, moeda) {
        return $.ajax({
            type: "POST",
            url: basePath + "/DemonstrativoPagamento/Pesquisar",
            data: {
                codigoPrestador: codigoPrestador,
                dataPagamento: dataPagamento,
                competencia: competencia,
                moeda: moeda
            },
            dataType: "json",
        });
    };
    self.exportpdf = function (id, moeda) {
        window.open(basePath + "DemonstrativoPagamento/Pdf?id=" + id + '&moeda=' + moeda);
    };
    self.getXmlPagamento = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "/DemonstrativoPagamento/XmlPagamento",
            data: {
                id: id
            },
            dataType: "json",
        });
    };
}
function PagamentoPrestadorRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarPagamentoPrestador?param=", cryptography(param));
        window.open(url, "_blank");
    };
}

function EmpresaRepository() {
    var self = this;

    self.search = function (value) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Empresa/SearchEmpresas",
            data: JSON.stringify({ value: value }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };

    self.getEmails = function (codigoEmpresa) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Empresa/GetEmails",
            data: { codigoEmpresa: codigoEmpresa },
            dataType: "json",
            contentType: 'application/json;',
        });
    };

    self.searchSimularAdesao = function (value, cidade) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Empresa/SearchEmpresasSimularAdesao",
            data: JSON.stringify({ value: value, cidade: cidade }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.getBeneficiariosAtivos = function (param) {
        return get("Empresa/GetBeneficiariosAtivos", param);
    };
    self.getAtestadosEmitidos = function (param) {
        return get("Empresa/getAtestadosEmitidos", param);
    };
    self.getDadosEmpresa = function (param) {
        return get("Empresa/GetDadosEmpresa", cryptography(param));
    };
    self.getReajustes = function (codEmpresa, page) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Empresa/GetReajustes"),
            data: {
                param: cryptography({
                    CodigoEmpresa: codEmpresa,
                    Page: page
                })
            }
        });
    }
    self.getProcedimentosPendentes = function (param) {
        return get("Empresa/GetProcedimentosPendentes", param);
    };
    self.getBeneficiariosUnidade = function (param) {
        return get("Empresa/GetBeneficiariosUnidade", param);
    };
    self.getBeneficiariosFaixaPlano = function (param) {
        return get("Empresa/GetBeneficiariosFaixaPlano", param);
    };
    self.getBeneficiariosFaixaPlanoDetalhe = function (param) {
        return get("Empresa/GetBeneficiariosFaixaPlanoDetalhe", param);
    };
    self.getDocumentosAssociados = function (param) {
        return get("Empresa/GetDocumentosAssociados", param);
    };
    self.realizarAlteracaoDadosCadastrais = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "Empresa/RealizarAlteracaoDadosCadastrais",
            data: { param: cryptography(model) },
            cache: false,
        });
    };

    self.getInfoAlteracaoCadastral = function (param) {
        return get("Empresa/GetInfoAlteracaoCadastral", cryptography(param));
    };
}
function UsuarioRepository() {
    var self = this;

    self.search = function (value) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Usuario/SearchUsuarios",
            data: JSON.stringify({ value: value }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.searchFacPlan = function (value) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Usuario/SearchUsuariosFacPlan",
            data: JSON.stringify({ value: value }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
}
function PedidoAlteracaoCadastralRepository() {
    var self = this;

    self.pesquisarAlteracoesBeneficiarios = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/PesquisarAlteracoesBeneficiarios",
            data: JSON.stringify(data),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.aprovarAlteracoes = function (idPedido) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/AprovarAlteracoes",
            data: JSON.stringify({
                idPedido: idPedido
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.aprovarAlteracaoCpfComBeneficiarioDuplicado = function (idPedido) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/AprovarAlteracaoCpfComBeneficiarioDuplicado",
            data: JSON.stringify({
                idPedido: idPedido
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.reprovarAlteracaoCpfComBeneficiarioDuplicado = function (idPedido) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/ReprovarAlteracaoCpfComBeneficiarioDuplicado",
            data: JSON.stringify({
                idPedido: idPedido
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.aprovarAlteracoesDocumentoAnexo = function (idPedido, tipoDocumento, numeroDocumento, inicioVigencia) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/AprovarAlteracoesDocumentoAnexo",
            data: JSON.stringify({
                idPedido: idPedido,
                tipoDocumento: tipoDocumento,
                numeroDocumento: numeroDocumento,
                inicioVigencia: inicioVigencia
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.reprovarAlteracoes = function (idPedido) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/ReprovarAlteracoes",
            data: JSON.stringify({
                idPedido: idPedido
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.aprovarTodasAlteracoes = function (pedidos) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/AprovarTodos",
            data: JSON.stringify({
                pedidos: pedidos
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.reprovarTodasAlteracoes = function (pedidos) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/ReprovarTodos",
            data: JSON.stringify({
                pedidos: pedidos
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.enviarEmailAlteracao = function (idPedido, assunto, corpo) {
        return $.ajax({
            type: "POST",
            url: basePath + "/PedidoAlteracaoCadastral/EmailAlteracao",
            data: JSON.stringify({
                idPedido: idPedido,
                assunto: assunto,
                corpo: corpo
            }),
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.exportarAlteracoesBeneficiarios = function (param) {
        var url = basePath.concat("PedidoAlteracaoCadastral/ExportarAlteracoesBeneficiarios?param=", param);
        window.open(url, "_blank");
    };
}
function BeneficiarioRepository() {
    var self = this;

    self.pesquisarBeneficiarios = function (texto) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Beneficiario/PesquisarBeneficiarios",
            data: { text: texto },
            dataType: "json",
            contentType: 'application/json;',
        });
    };
    self.getEmails = function (codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Beneficiario/GetEmails",
            data: { codigoBeneficiario: codigoBeneficiario },
            dataType: "json",
            contentType: 'application/json;',
        });
    };

    self.getCarteiraReciprocidade = function (codigoBeneficiario) {

        var param = { Value: codigoBeneficiario };

        return get("Beneficiario/GetCarteiraReciprocidade", cryptography(param));
    };

    self.getPerfil = function (param) {
        return get("Beneficiario/Get", param);
    };
    self.ImprimirUtilizacaoBeneficiario = function (param) {
        var url = basePath.concat("RelatorioPinSSBeneficiario/ImprimirUtilizacaoBeneficiario?param=", param);
        window.open(url, "_blank");
    };
    self.getImpressaoCarteiraBeneficiario = function (param) {
        return get("Beneficiario/GetImpressaoCarteiraBeneficiario", param);
    };
    self.getElegibilidade = function (param) {
        return get("Beneficiario/GetElegibilidade", cryptography(param));
    };
    self.getHistoricoSuspensao = function (param) {
        return get("Beneficiario/GetHistoricoSuspensao", cryptography(param));
    };

    self.getUtilizacaoBeneficiario = function (param) {
        return get("Beneficiario/GetAbaUtilizacoes", cryptography(param));
    };
    self.salvar = function (beneficiario) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Beneficiario/Post",
            data: beneficiario.getModel(),
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.emitirTermo = function (codigo, acaoId) {
        var payload = {
            CodigoBeneficiario: codigo,
            IdAcao: acaoId
        };
        var paramBase64 = window.btoa(JSON.stringify(payload));
        var url = basePath + "/Beneficiario/EmitirTermoDadosBeneciciario?param=" + encodeURIComponent(paramBase64);
        window.open(url, '_blank');
    };
    self.getDadosBeneficiario = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Beneficiario/GetDadosBeneficiario",
            data: model,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.beneficiarioPossuiServicosSemConciliar = function (id) {
        return get("Beneficiario/BeneficiarioPossuiServicosSemConciliar", cryptography({ Value: id }));
    };
    self.validarSolicitacaoSegundaVia = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Beneficiario/ValidarSolicitacaoSegundaVia",
            data: {
                id: id
            },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getDependentesBeneficiario = function (param) {
        return get("Beneficiario/GetDependentesBeneficiario", cryptography(param));
    };
    self.solicitarSegundaViaCarteira = function (parametros) {
        return $.ajax({
            type: "POST",
            url: basePath + "Beneficiario/SolicitarSegundaViaCarteira",
            data: parametros,
            contentType: 'application/json',
            dataType: 'json'
        });
    };
    self.searchBeneficiario = function (param) {
        return get("Beneficiario/SearchBeneficiario", param);
    };
    self.getBeneficiario = function (id, async) {
        return $.ajax({
            type: "GET",
            async: async,
            url: basePath + "/Beneficiario/GetBeneficiario",
            data: { id: id },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getLimitesBeneficiario = function (param) {
        return get("Beneficiario/GetLimitesBeneficiario", cryptography(param));
    };
    self.getAditivosVinculado = function (param) {
        return get("Beneficiario/GetAditivosVinculado", cryptography(param));
    };
    self.getServicosProgramaBeneficios = function (id) {
        var param = { Value: id };
        return get("Beneficiario/GetServicosProgramaBeneficios", cryptography(param));
    };
    self.getProcedimentosPendentes = function (param) {
        return get("Beneficiario/GetProcedimentosPendentes", param);
    };
    self.imprimirDadosBeneficiario = function (param) {
        var url = basePath.concat("Beneficiario/ImprimirDadosBeneficiario?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.getBeneficiarioByNumeroDaCarteira = function (numeroDaCarteira, nomeSegurado) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Guias/GetBeneficiarioByNumeroDaCarteira",
            data: { numeroDaCarteira: numeroDaCarteira, nomeSegurado: nomeSegurado },
            dataType: "json",
            contentType: 'application/json;',
        });
    };

    self.getAnotacoesAdministrativas = function (id) {
        var param = {
            Id: id
        };
        return get("Beneficiario/GetAnotacoesAdministrativas", cryptography(param));
    };

    //self.emitirTermo = function (param) {
    //    var url = basePath.concat("Beneficiario/EmitirTermoDadosBeneciciario?param=", param);
    //    window.open(url, "_blank");
    //};
    self.getGrupoServicosProgramaBeneficios = function (id) {
        var param = { Value: id };
        return get("Beneficiario/GetGrupoServicosProgramaBeneficios", cryptography(param));
    };
}
function AvisosEArquivosRepository() {
    var self = this;

    self.CheckAcessoOcultarAviso = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "Acesso/VerificaAcessoOcultarAvisos",
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.GetCategorias = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "Avisos/GetListaCategoria",
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.GetAvisos = function (idCategoria) {
        return $.ajax({
            type: "GET",
            url: basePath + "Avisos/GetAvisos",
            data: { idCategoria: idCategoria },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.DownloadArquivo = function (idAviso, arquivo) {
        return $.post(basePath + "Avisos/GetDiretorioArquivos");
    };
    self.MarcarComoLida = function (idAviso) {
        return $.ajax({
            type: "POST",
            url: basePath + "Avisos/MarcarComoLido",
            data: { idAviso: idAviso },
            cache: false
        });
    };
    self.MarcarComoOcultado = function (idAviso) {
        return $.ajax({
            type: "POST",
            url: basePath + "Avisos/MarcarComoOcultado",
            data: { idAviso: idAviso },
            cache: false
        });
    };
    self.OcultarAvisos = function (idAvisos) {
        return $.ajax({
            type: "POST",
            url: basePath + "Avisos/OcultarAvisos",
            data: JSON.stringify(idAvisos),
            dataType: 'json',
            contentType: 'application/json',
            cache: false
        });
    };
    self.GetDocumentosVencidos = function (idAvisos) {
        return $.ajax({
            type: "GET",
            url: basePath + "Avisos/GetDocumentosVencidos",
            dataType: 'json',
            contentType: 'application/json',
        });
    };
}
function EnderecoRepository() {
    var self = this;

    self.pesquisarBairro = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "Biometria/UtilizaApplet",
            data: {
                codigoPrestador: self.codigoPrestador(),
                dataPagamento: self.dataPagamento(),
                competencia: self.competencia()
            },
            cache: false,
            async: false,
        });
    };
    self.pesquisarBairro = function (criterio, codigoCidade) {
        return $.ajax({
            type: "POST",
            url: basePath + "Endereco/BuscarBairro",
            data: { criterio: criterio, codigoCidade: codigoCidade },
            cache: false,
        });
    };
    self.pesquisarCep = function (cep) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Endereco/BuscarEndereco/",
            data: {
                cep: cep.replace(/\.|\-/g, '')
            },
            cache: false
        });
    };

    self.buscarCep = function searchEndereco(cep) {
        var result;
        $.ajax({
            url: basePath + "/Endereco/BuscarEndereco/",
            data: {
                "cep": cep
            },
            method: "GET",
            async: false,
            success: function (data) {
                result = data;
            }
        });
        return result;
    }

    self.pesquisarCepFacPlan = function (cep) {
        return $.ajax({
            type: "GET",
            url: basePath + "Endereco/BuscarEnderecoFacPlan",
            data: {
                cep: cep.replace(/\.|\-/g, '')
            },
            cache: false
        });
    };
    self.listarTipoCep = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "Endereco/ListarTipoCep",
            dataType: 'json',
            contentType: 'application/json',
            data: {},
            cache: false
        });
    };
    self.pesquisarCidade = function (criterio, siglaUf) {
        return $.ajax({
            type: "POST",
            url: basePath + "Endereco/BuscarCidade",
            data: { criterio: criterio, estado: siglaUf },
            cache: false,
        });
    };
    self.listarEstados = function (criterio) {
        var estados =
            [{
                "Sigla": "AC",
                "Nome": "Acre"
            },
            {
                "Sigla": "AL",
                "Nome": "Alagoas"
            },
            {
                "Sigla": "AM",
                "Nome": "Amazonas"
            },
            {
                "Sigla": "AP",
                "Nome": "Amapá"
            },
            {
                "Sigla": "BA",
                "Nome": "Bahia"
            },
            {
                "Sigla": "CE",
                "Nome": "Ceará"
            },
            {
                "Sigla": "DF",
                "Nome": "Distrito Federal"
            },
            {
                "Sigla": "ES",
                "Nome": "Espírito Santo"
            },
            {
                "Sigla": "GO",
                "Nome": "Goiás"
            },
            {
                "Sigla": "MA",
                "Nome": "Maranhão"
            },
            {
                "Sigla": "MG",
                "Nome": "Minas Gerais"
            },
            {
                "Sigla": "MS",
                "Nome": "Mato Grosso do Sul"
            },
            {
                "Sigla": "MT",
                "Nome": "Mato Grosso"
            },
            {
                "Sigla": "PA",
                "Nome": "Pará"
            },
            {
                "Sigla": "PB",
                "Nome": "Paraíba"
            },
            {
                "Sigla": "PE",
                "Nome": "Pernambuco"
            },
            {
                "Sigla": "PI",
                "Nome": "Piauí"
            },
            {
                "Sigla": "PR",
                "Nome": "Paraná"
            },
            {
                "Sigla": "RJ",
                "Nome": "Rio de Janeiro"
            },
            {
                "Sigla": "RN",
                "Nome": "Rio Grande do Norte"
            },
            {
                "Sigla": "RO",
                "Nome": "Rondônia"
            },
            {
                "Sigla": "RR",
                "Nome": "Roraima"
            },
            {
                "Sigla": "RS",
                "Nome": "Rio Grande do Sul"
            },
            {
                "Sigla": "SC",
                "Nome": "Santa Catarina"
            },
            {
                "Sigla": "SE",
                "Nome": "Sergipe"
            },
            {
                "Sigla": "SP",
                "Nome": "São Paulo"
            },
            {
                "Sigla": "TO",
                "Nome": "Tocantins"
            }]

        if (criterio) {
            var estadosFiltrados = [];
            estados.map(function (i) {
                if (i.Sigla.contains(criterio))
                    estadosFiltrados.push(i);
            });
            return estadosFiltrados;
        }
        return estados;
    };
}
function GestaoDocumentoRepository() {
    var self = this;

    self.listarTipoAnexo = function () {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Upload/GetTipoAnexoEnum"),
            data: {},
            async: false,
            cache: false
        });
    };

    self.download = function (id) {
        var param = { Value: id };
        window.open(basePath + "Download/GetFileGestaoDocumento?param=" + cryptography(param), '_blank', '');
    };

}
function TransacaoANSRepository() {
    var self = this;

    self.pesquisar = function (filtro) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("TransacoesANS/Pesquisar"),
            data: filtro
        });
    };
}

function ContatoClienteRepository() {
    var self = this;

    self.getRegistros = function (param) {
        return get("ContatoDeCliente/GetRegistros", cryptography(param));
    };

    self.getAnotacoes = function (param) {
        return get("ContatoDeCliente/GetAnotacoes", cryptography(param));
    };

    self.getAnexos = function (param) {
        return get("ContatoDeCliente/GetAnexos", cryptography(param));
    };

    self.getCategorias = function (param) {
        return get("ContatoDeCliente/GetCategorias", cryptography(param));
    };

    self.getSubCategorias = function (param) {
        return get("ContatoDeCliente/GetSubCategorias", cryptography(param));
    };

    self.getTipoAnexoCategoria = function (param) {
        return get("ContatoDeCliente/GetTipoAnexoCategoria", cryptography(param));
    };

    self.getMatriculaBeneficiario = function (matricula) {
        var param = { Value: matricula };
        return get("ContatoDeCliente/GetMatriculaBeneficiario", cryptography(param));
    };

    self.getExtensoesAnexos = function () {
        return getWithoutParam("ContatoDeCliente/GetExtensoesAnexos");
    };

    self.salvar = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/Salvar", param, true);
    };

    self.getTamanhoMaxAnexos = function () {
        return $.ajax({
            type: "POST",
            cache: false,
            async: false,
            dataType: "json",
            contentType: 'application/json',
            url: basePath.concat("ContatoDeCliente/GetTamanhoMaxAnexos"),
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };

    self.getPlaceHolderTextoRegistro = function () {
        return $.ajax({
            type: "POST",
            cache: false,
            async: false,
            dataType: "json",
            contentType: 'application/json',
            url: basePath.concat("ContatoDeCliente/Getplaceholdertextoregistro"),
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };

    self.aprovarProposta = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/Proposta", param, true);
    };

    self.alterarNivelSatisfacao = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/AlterarNivelSatisfacao", param, true);
    };

    self.encerrar = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/EncerrarChamado", param, true);
    };

    self.adicionarContatoEncerrarChamado = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/AdicionarContatoEncerrarChamado", param, true);
    };

    self.autorizar = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/AutorizarChamado", param, true);
    };

    self.getAletas = function (idChamado) {
        var param = { param: cryptography({ Value: idChamado }) };
        return postData("ContatoDeCliente/GetAlertasChamdos", param, true);
    };

    self.verificarPreenchimentoFormulario = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/VerificarPreenchimentoFormulario", param, true);
    };

    self.concluirPreenchimentoDosAlertas = function (model) {
        var param = { param: cryptography(model) };
        return postData("ContatoDeCliente/ConcluirPreenchimentoDosAlertas", param, true);
    };

    self.downloadFile = function (tipoDeContato, idArquivo, idContato) {
        var model =
        {
            Id: idContato,
            IdArquivo: idArquivo,
            TipoDeContato: tipoDeContato
        };
        var url = basePath.concat("ContatoDeCliente/DownloadArquivo?param=", cryptography(model));
        window.open(url, "_blank");
    };

    self.getTipoQuestionario = function (param) {
        return get("ContatoDeCliente/GetTipoQuestionario", cryptography(param));
    };

}
function PrestadorRepository() {
    var self = this;

    self.salvarPerfil = function (perfil) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Profile/Salvar"),
            data: perfil
        });
    };
    self.enviarInformacoesAltaOuInternacao = function (dados) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/EnviarInformacoesAltaOuInternacao"),
            data: dados
        });
    };
    self.pesquisarPrestadoresEmpresas = function (texto) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Prestador/PesquisarPrestadoresEmpresas"),
            data: {
                text: texto
            }
        });
    };
    self.getPrestador = function (param) {
        return get("Prestador/GetByCpfOuCnpj", cryptography(param));
    };
    self.verificarElegibilidadeProcedimento = function (param) {
        return get("Prestador/VerificarElegibilidadeProcedimento", cryptography(param));
    };
    self.searchPrestador = function (value, incluirLaboratorio, incluirEmpresaMedica, ehPrestadorOdonto, incluirNomeFantasia, somentePrestadorCredenciado) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/SearchAnyPrestador"),
            data: {
                value: value,
                incluirLaboratorio: incluirLaboratorio,
                incluirEmpresaMedica: incluirEmpresaMedica,
                ehPrestadorOdonto: ehPrestadorOdonto,
                incluirNomeFantasia: incluirNomeFantasia,
                somentePrestadorCredenciado: somentePrestadorCredenciado ? true : false
            },
            cache: false
        });
    };
    self.searchHospital = function (value) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/SearchHospital"),
            data: {
                value: value
            },
            cache: false
        });
    };
    self.procurarExecutanteGuiaPor = function (value, ehPrestadorOdonto) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/ProcurarExecutanteGuiaPor"),
            data: {
                value: value,
                ehPrestadorOdonto: ehPrestadorOdonto ? true : false,
            },
            cache: false
        });
    }
    self.searchPrestadorModel = function (value, incluirLaboratorio, incluirEmpresaMedica, ehPrestadorOdonto) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/SearchAnyPrestadorModel"),
            data: {
                value: value,
                incluirLaboratorio: incluirLaboratorio,
                incluirEmpresaMedica: incluirEmpresaMedica,
                ehPrestadorOdonto: ehPrestadorOdonto
            },
            cache: false
        });
    };
    self.consultaProcedimentos = function (param) {
        return get("Prestador/GetConsultaProcedimentos", cryptography(param));
    };
    self.consultaProcedimentosToPdf = function (param) {
        var url = basePath.concat("Prestador/Impressao?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.consultaProcedimentosToCsv = function (param) {
        var url = basePath.concat("Prestador/ExportarProcedimentosCSV?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.searchPrestadorWebLogin = function (value, incluirLaboratorio, incluirEmpresaMedica, ehPrestadorOdonto, somenteHospitais, somenteComFaturamentoAutomatico,
        codigoEmpresaMedica, somenteLaboratorios, somenteMedicos, ExibirPrestadorCanceladoApenasNaPesquisa) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/SearchAnyPrestadorDoWebLogin"),
            data: {
                value: value,
                incluirLaboratorio: incluirLaboratorio,
                incluirEmpresaMedica: incluirEmpresaMedica,
                ehPrestadorOdonto: ehPrestadorOdonto,
                somenteHospitais: somenteHospitais,
                somenteComFaturamentoAutomatico: somenteComFaturamentoAutomatico,
                codigoEmpresaMedica: codigoEmpresaMedica,
                somenteLaboratorios: somenteLaboratorios,
                somenteMedicos: somenteMedicos,
                ExibirPrestadorCanceladoApenasNaPesquisa: ExibirPrestadorCanceladoApenasNaPesquisa
            },
            cache: false
        });
    };
    self.searchPeritos = function (value, peritoInterno, async) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Prestador/SearchPerito"),
            data: {
                value: value,
                peritoInterno: peritoInterno
            },
            async: async,
            cache: false
        });
    };
    self.getContratadoGuiaConsultaByCodigo = function (async, model) {
        //Model Precisa
        //{idContratado, nomeContratado, incluirLaboratorio, incluirEmpresaMedica,  somentePrestadoresDoWebLogin, somenteComFaturamentoAutomatico, ehPrestadorOdonto}
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("GuiasTISS/GuiaConsulta/GetContratadoGuiaConsultaByCodigo"),
            data: model,
            async: async,
            cache: false
        });
    };
    self.getTabelaPrestador = function (codigoPrestador) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Prestador/GetTabelaPrestador"),
            data: {
                codigoPrestador: codigoPrestador
            },
            cache: false
        });
    };
    self.getEnderecosAtendimentoPrestador = function (param) {
        return get("Prestador/GetEnderecosAtendimento", cryptography(param));
    };
}

function CartaPortabilidadeRepository() {
    var self = this;

    self.gerarPDF = function (id, emitirFamilia) {
        // return get("CartaPortabilidade/GerarCarta", id);

        var model = {
            CodSeg: id,
            EmiteCartaFamilia: emitirFamilia
        };

        var url = basePath.concat("CartaPortabilidade/GerarCarta?param=", cryptography(model));
        window.open(url, "_blank");
    };
}

function SolicitacaoReembolsoRepository() {
    var self = this;

    self.consultar = function (filtro) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Reembolso/ConsultarSolicitacoes"),
            data: filtro
        });
    };
    self.consultarItens = function (id) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Reembolso/ConsultarItensSolicitacao"),
            data: {
                id: id
            }
        });
    };

    self.solicitar = function (reembolso) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Reembolso/Solicitar",
            data: reembolso,
            dataType: "json",
            contentType: "application/json",
        });
    };
    self.removerItem = function (id, beneficiarioId) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Reembolso/RemoverItemSolicitacao",
            data: { id: id, BeneficiarioId: beneficiarioId },
            dataType: "json",
        });
    };
    self.getModelSolicitacao = function (param) {
        return get("/Reembolso/GetModelSolicitacao", cryptography(param));
    };

    self.getProcedimentoNaoCoberto = function (param) {
        return get("/Reembolso/GetProcedimentoNaoCoberto", cryptography(param), false);
    };

    self.getIdProgramaBeneficio = function (param) {
        return get("/Reembolso/GetIdProgramaBeneficio", cryptography(param), false);
    };

    self.pesquisarProcedimentos = function (texto, prestadorCpfCnpj, tipoPrestador, dataAtendimento, codigoBeneficiario, tipoProcedimento, ufTabelaProcedimento, codTabelaUsoContinuoPadrao, codigoGrupoReembolso) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Reembolso/PesquisarProcedimento",
            data: {
                text: texto,
                prestadorCpfCnpj: prestadorCpfCnpj,
                tipoPrestador: tipoPrestador,
                dataAtendimento: dataAtendimento,
                codigoBeneficiario: codigoBeneficiario,
                tipoProcedimentoReembolso: tipoProcedimento,
                ufTabelaProcedimento: ufTabelaProcedimento,
                codTabelaMedicamentoUsoContinuoPadrao: codTabelaUsoContinuoPadrao,
                codigoGrupoReembolso: codigoGrupoReembolso
            },
            dataType: "json",
            contentType: "application/json",
        });
    };

    self.getMedicamentosPrescricaoMedica = function (codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Reembolso/GetMedicamentosPrescricaoMedica",
            data: { codigoBeneficiario: codigoBeneficiario },
            dataType: "json",
            contentType: "application/json",
        });
    };

    self.getGrupoReembolsoPorPlano = function (codigoPlano) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Reembolso/GetGrupoReembolsoPorPlano",
            data: { codigoPlano: codigoPlano },
            dataType: "json",
            contentType: "application/json",
        });
    };

    //implemento do card 181704 para buscar o plano na data de atendimento
    self.GetPlanoNaDataAtendimento = function (codigoBeneficiario, dataAtendimento) {
        return $.ajax({
            type: "GET",
            url: basePath + "Reembolso/GetPlanoNaDataAtendimento",
            data: {
                codigoBeneficiario: codigoBeneficiario,
                dataAtendimento: moment(dataAtendimento).format("YYYY-MM-DD")
            },
            dataType: "json"
        });
    };


    self.existeSolicitacaoSalva = function (reembolso) {
        return $.ajax({
            type: "POST",
            url: basePath + "/Reembolso/ExisteSolicitacaoSalva",
            data: reembolso,
            dataType: "json",
            contentType: "application/json",
        });
    };
    self.existeCpfParaBeneficiario = function (param) {
        return get("Reembolso/ExisteCpfParaBeneficiario", cryptography(param));
    };
    self.getNomePrestadorNoItemSolicitacao = function (param) {
        return get("Reembolso/ExistePrestadorNaSolicitacao", cryptography(param));
    };

    self.verificaSePodeImprimirCartaIndeferimento = function (id) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Reembolso/VerificaSePodeImprimirCartaIndeferimento"),
            data: {
                id: id
            }
        });
    };

    self.imprimirCartaIndeferimento = function (id) {

        var model = { Value: id };
        var url = basePath.concat("Reembolso/ImprimirCartaIndeferimento?param=", cryptography(model));
        window.open(url, "_blank");
    };

    self.imprimirDadosReembolso = function (id) {
        var param = { Value: id };
        window.open(basePath + "Reembolso/GetRelSolicitacao?param=" + cryptography(param), '_blank', '');
    };

    self.enviarEmailDetalhamento = function (model) {
        return get("Reembolso/EnviarEmailDetalhamento", cryptography(model));
    }
}
function TipoReembolsoRepository() {
    var self = this;

    self.get = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "/Reembolso/TiposReembolso",
            dataType: "json",
            contentType: "application/json",
        });
    };
}
function INSSRepository() {
    var self = this;

    self.gerarRelatorio = function (codPrestador, mes, ano) {
        return $.ajax({
            type: "POST",
            url: basePath + "INSS/GerarRelatorioMensalINSS",
            data: { codPrestador: codPrestador, mes: mes, ano: ano },
            cache: false,
        });
    };
    self.imprimir = function (param) {
        var url = basePath.concat("INSS/Pdf?param=", param);
        window.open(url, "_blank");
    };
}
function DespesaMedicaRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("DespesaMedica/Relatorio", cryptography(param));
    };
    self.exportpdf = function (param) {
        var url = basePath.concat("DespesaMedica/Pdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.enviarEmail = function (model) {
        return get("DespesaMedica/EnviarEmail", cryptography(model));
    }
}
function EnvioRelatorioEmailRepository() {
    var self = this;

    self.despesaMedica = function (param) {
        return get("DespesaMedica/SalvarRelatorioServidor", cryptography(param));
    };
    self.demonstrativoUtilizacao = function (param) {
        return get("DemonstrativoUtilizacao/Gerar", cryptography(param));
    };
    self.enviarEmail = function (param) {
        return get("EnvioRelatorioEmail/EnviarEmail", cryptography(param));
    };
    self.enviarEmailDemonstrativoUtilizacao = function (param) {
        return get("EnvioRelatorioEmail/EnviarEmailDemonstrativoUtilizacao", cryptography(param));
    };
    self.enviarBoletoIndividualPorEmail = function (boletoId, email) {
        return $.ajax({
            type: "GET",
            url: basePath + "EnvioRelatorioEmail/EnvioBoletoPorEmail",
            data: { boletoId: boletoId, email: email },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.enviarBoletoIndividualEmpresaPorEmail = function (boletoId, email) {
        return $.ajax({
            type: "GET",
            url: basePath + "EnvioRelatorioEmail/EnvioBoletoEmpresaPorEmail",
            data: { boletoId: boletoId, email: email },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.downloadEntidadesSemEmail = function (tipoEntidade) {
        var url = basePath + "EnvioRelatorioEmail/DownloadEntidadesSemEmail?tipoEntidade=" + tipoEntidade
        var w = window.open(url);
    };
    self.downloadEntidadesSemEmailDemonstrativoUtilizacao = function (tipoEntidade, competencia) {
        var url = basePath + "EnvioRelatorioEmail/DownloadEntidadesSemEmail?tipoEntidade=" + tipoEntidade + "&competencia=" + competencia
        var w = window.open(url);
    };
    self.downloadRelatoriosEntidadesSemEmailDemonstrativoUtilizacao = function (competencia, page, hash, fazerDownload) {
        if (fazerDownload) {
            var url = basePath + "EnvioRelatorioEmail/DownloadRelatoriosEntidadesSemEmail?competencia=" + competencia + "&page=" + page + "&hash=" + hash + "&efetuarMerge=" + fazerDownload;
            var w = window.open(url);
        } else {
            return $.ajax({
                type: "GET",
                url: basePath + "EnvioRelatorioEmail/DownloadRelatoriosEntidadesSemEmail?competencia=" + competencia + "&page=" + page + "&hash=" + hash + "&efetuarMerge=" + fazerDownload
            });
        }
    };
    self.countAllBeneficiarioTitularOuRecebeDemonstrativo = function (competencia) {
        return $.ajax({
            type: "GET",
            url: basePath + "EnvioRelatorioEmail/CountAllBeneficiarioTitularOuRecebeDemonstrativo?competencia=" + competencia
        });
    };
    self.totalRelatoriosEntidadesSemEmailDemonstrativoUtilizacao = function (competencia) {
        return $.ajax({
            type: "GET",
            url: basePath + "EnvioRelatorioEmail/TotalRelatoriosEntidadesSemEmail?competencia=" + competencia
        });
    };
}
function ImpressaoCarteiraRepository() {
    var self = this;

    self.getCarteirasPendentesLoteDeEntrega = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "Carteira/GetCarteirasPendentesPorLocalDeEntrega",
            data: JSON.stringify({ Value: data }),
            dataType: "json",
            contentType: "application/json"
        });
    }

    self.getLotesDeEntregaCarteira = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("Carteira/GetLotesDeEntregaCarteira"),
            data: JSON.stringify({ Value: data.CodigoLocalEntrega }),
            dataType: "json",
            contentType: "application/json"
        });
    }

    self.createLoteDeEntregaCarteira = function (data) {
        var newLote = $.ajax({
            type: "POST",
            async: false,
            cache: false,
            url: basePath.concat("Carteira/CreateLoteDeEntregaCarteira"),
            data: JSON.stringify({ Value: data }),
            dataType: "json",
            contentType: "application/json"
        });

        if (newLote.status == 200)
            facil.noty.success('Sucesso', 'Lote criado com sucesso!', true);
        else
            facil.noty.error('Erro', newLote.statusText, true);

        return newLote;
    }

    self.receberLoteDeEntregaCarteira = function (data) {
        var newLote = $.ajax({
            type: "POST",
            async: false,
            cache: false,
            url: basePath + "Carteira/ReceberLoteDeEntregaCarteira",
            data: JSON.stringify({ Value: data }),
            dataType: "json",
            contentType: "application/json"
        });
        console.log(data);

        if (newLote.status == 200)
            facil.noty.success('Sucesso', 'Lote confirmado com sucesso!', true);
        else
            facil.noty.error('Erro', newLote.statusText, true);

        return newLote;
    }

    self.validaImprimir = function (codigoBeneficiario, imprimirFamiliares, dataForcaValidade) {
        return $.ajax({
            type: "GET",
            url: basePath + "ImpressaoCarteira/ValidaImprimir",
            data: { codigoBeneficiario: codigoBeneficiario, imprimirFamiliares: imprimirFamiliares, DataValidadeForcada: dataForcaValidade },
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.imprimir = function (codigoBeneficiario, dataForcaValidade, imprimirFamiliares) {
        var model =
        {
            CodigoBeneficiario: codigoBeneficiario,
            ImprimirTodaFamilia: imprimirFamiliares,
            DataValidadeForcada: dataForcaValidade,
            ModeloImpressoraInfraero: null,
            LayoutImpressaoCarteira: null
        };

        window.open(basePath + "ImpressaoCarteira/Imprimir?param=" + cryptography(model));
    };
    self.imprimirNovo = function (model) {
        window.open(basePath + "ImpressaoCarteira/ImprimirNovo?param=" + cryptography(model));
    };
    self.ImprimirCarteiraJaEmitida = function (param) {
        var url = basePath.concat("ImpressaoCarteira/ImprimirCarteiraJaEmitida?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("ImpressaoCarteira/EnviarCarteiraEmail", cryptography(model));
    }

    self.getImagemCarteira = function (param) {
        return get("Carteira/GetImagemCarteira", cryptography(param));
    };
    self.getNumerosCarteira = function (param) {
        return get("Carteira/GetNumerosCarteira", cryptography(param));
    };

    self.getBeneficiariosConfirmarCarteira = function (param) {
        return get("Carteira/GetBeneficiariosConfirmarCarteira", cryptography(param));
    };

    self.getBeneficiariosEmissaoCarteira = function (param) {
        return get("Carteira/GetBeneficiariosEmissaoCarteira", cryptography(param));
    };

    self.emitirCarteiras = function (itens) {
        var model = { Beneficiarios: itens }
        window.open(basePath + "Carteira/EmitirCarteiras?param=" + cryptography(model));
    };

    self.getBeneficiariosConfirmarCarteira = function (param) {
        return get("Carteira/GetBeneficiariosConfirmarCarteira", cryptography(param));
    };

    self.getBeneficiariosEmissaoCarteira = function (param) {
        return get("Carteira/GetBeneficiariosEmissaoCarteira", cryptography(param));
    };

    self.emitirCarteiras = function (itens) {
        var model = { Beneficiarios: itens }
        window.open(basePath + "Carteira/EmitirCarteiras?param=" + cryptography(model));
    };

}
function RelatorioCarteirasImpressasRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("RelatorioCarteirasImpressas/GetCarteirasImpressas", cryptography(param));
    }

    self.downloadCSV = function (param) {
        var url = basePath.concat("RelatorioCarteirasImpressas/DownloadCSV?param=", cryptography(param));
        window.open(url, "_blank");
    }
}
function DocumentosAssociadosRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("DocumentosAssociados/Pesquisar", cryptography(param));
    };
    self.pesquisarByCredenciado = function (data) {
        return $.ajax({
            type: "GET",
            url: basePath + "DocumentosAssociadosCredenciado/Pesquisar",
            data: data,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.searchDocAsssociadosByCredenciado = function (credenciado) {
        return $.ajax({
            type: "GET",
            url: basePath + "DocumentosAssociadosCredenciado/GetAllDocAssociadosByCredenciado",
            data: {
                codCredenciado: credenciado.Codigo,
                tipoCredenciado: credenciado.TipoEntidade,
                onlyVisible: true
            },
        });
    };
    self.file = function (data) {
        return $.ajax({
            type: "GET",
            url: basePath + "DocumentosAssociadosCredenciado/file?id=" + data,
            cache: false,
            contentType: false,
            processData: false
        });
    };

    self.download = function (data) {
        var param = {
            Id: data.Id,
            EnderecoArquivo: data.EnderecoArquivo
        };
        return $.ajax({
            type: "POST",
            contentType: 'application/json',
            url: basePath.concat("DocumentosAssociadosCredenciado/FileByParam"),
            data: JSON.stringify(param),
            cache: false
        });
    };

    self.newFile = function (formData, ehCredenciado) {
        if (ehCredenciado) {
            return $.ajax({
                type: "POST",
                url: basePath + "DocumentosAssociadosCredenciado/NovoArquivo",
                data: formData,
                cache: false,
                contentType: false,
                processData: false
            });
        }
        else {
            return $.ajax({
                type: "POST",
                url: basePath + "DocumentosAssociados/NovoArquivo",
                data: formData,
                cache: false,
                contentType: false,
                processData: false
            });
        }
    };
}
function ExtratoCobrancaRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("ExtratoCobranca/Relatorio", cryptography(param));
    };
    self.exportpdf = function (param) {
        var url = basePath.concat("ExtratoCobranca/Pdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.enviarEmail = function (model) {
        return get("ExtratoCobranca/EnviarEmail", cryptography(model));
    }
}

function ExtratoCobrancaFRGRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("ExtratoCobrancaFRG/Gerar", cryptography(param));
    };
    self.exportpdf = function (param) {
        var url = basePath.concat("ExtratoCobrancaFRG/GerarPdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.enviarEmail = function (model) {
        return get("ExtratoCobrancaFRG/EnviarEmail", cryptography(model));
    }
}
function BancoRepository() {
    var self = this;

    self.get = function (nome) {
        return $.ajax({
            type: "GET",
            url: basePath + "banco/get?nome=" + nome,
            dataType: "json",
        });
    };
}
function ServicosRepository() {
    var self = this;

    self.getAdicionaisFatura = function (fatura, tipo) {
        return $.ajax({
            type: "GET",
            url: basePath + "relatorios/getadicionaisfatura?fatura=" + fatura + '&tipo=' + tipo,
            dataType: "json",
        });
    };
    self.getXmlServicoAssync = function (codigoFatura, codigoPrestador, tipoPrestador, protocolo) {
        return $.ajax({
            type: "POST",
            async: false,
            cache: false,
            url: basePath + "Relatorios/GetXmlServicoAssync",
            data: {
                codigoFatura: codigoFatura,
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                protocolo: protocolo
            }
        });
    };
    self.CheckXmlServicoAssync = function (guid) {
        return $.ajax({
            type: "POST",
            async: false,
            cache: false,
            url: basePath + "Relatorios/CheckXmlServicoAssync",
            data: {
                guid: guid
            }
        });
    };
    self.getXmlServico = function (codigoFatura, codigoPrestador, tipoPrestador, protocolo) {
        return $.ajax({
            type: "POST",
            async: true,
            cache: false,
            url: basePath + "Relatorios/GetXmlServico",
            data: {
                codigoFatura: codigoFatura,
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador,
                protocolo: protocolo
            },
            timeout: 3600000
        });
    };
    self.getDadosPresdatorFatura = function (codigoPrestador) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            dataType: "json",
            url: basePath + "Faturas/BuscaPrestadorById",
            data: {
                codigoPrestador: codigoPrestador
            }
        });
    };
    self.getAnexosFatura = function (codigoFatura, codigoPrestador, tipoPrestador) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            url: basePath + "Faturas/GetAnexosFatura",
            data: {
                codigoFatura: codigoFatura,
                codigoPrestador: codigoPrestador,
                tipoPrestador: tipoPrestador
            },
            timeout: 3600000
        });
    };
    self.getNotaFatura = function (codigoFatura) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            url: basePath + "Faturas/GetNotaFatura",
            data: {
                codigoFatura: codigoFatura
            },
            timeout: 3600000
        });
    };
    self.addObservacaoFatura = function (codigoFatura, observacao) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            url: basePath + "Relatorios/AddObservacaoFatura",
            data: {
                chave: codigoFatura,
                observacao: observacao
            },
            timeout: 3600000
        });
    };
    self.getObservacaoFatura = function (codigoFatura) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            url: basePath + "Relatorios/GetObservacaoFatura",
            data: {
                chave: codigoFatura
            },
            timeout: 3600000
        });
    };
    self.downloadCSV = function (codigoFatura) {
        window.open('/Relatorios/DownloadCSV?param=' + cryptography({ Value: codigoFatura }), '_blank', '');
    };
    self.downloadPDFAnaliseContas = function (codigoFatura) {
        window.open('/Relatorios/DownloadPDFAnaliseContas?param=' + cryptography({ Value: codigoFatura }), '_blank', '');
    };
}
function ConselhoProfissionalRepository() {
    var self = this;

    self.get = function (nome) {
        return $.ajax({
            type: "GET",
            url: basePath + "conselhoprofissional/get?nome=" + nome,
            dataType: "json",
        });
    };
}
function UfRepository() {
    var self = this;

    self.get = function (nome) {
        return $.ajax({
            type: "GET",
            url: basePath + "uf/get?nome=" + nome,
            dataType: "json",
        });
    };
}
function TipoAtendimentoRepository() {
    var self = this;

    self.get = function (nome) {
        return $.ajax({
            type: "GET",
            url: basePath + "tipoatendimento/get?nome=" + nome,
            dataType: "json",
        });
    };
}
function DemonstrativoPagamentoBeneficiarioRepository() {
    var self = this;

    self.exportpdf = function (param) {
        var url = basePath.concat("DemonstrativoPagamentoBeneficiario/Export?param=", param);
        window.open(url, "_blank");
    };
}
function CoparticipacaoBeneficiarioRepository() {
    var self = this;

    self.getCoparticipacoes = function (param) {
        return get("CoparticipacoesBeneficiario/Localizar", cryptography(param));
    };
}
function SolicitacaoCancelamentoRepository() {
    var self = this;

    self.getBeneficiarios = function (param) {
        return get("SolicitacaoCancelamento/Localizar", cryptography(param), true);
    };
    self.enviarSolicitacaodeCancelamento = function (param) {
        return get("SolicitacaoCancelamento/EfetivarSolicitacaoCancelamento", cryptography(param));
    };
    self.getSoliciacoes = function (param) {
        return get("SolicitacaoCancelamento/GetSolicitacaoCancelamento", param, true);
    };
    self.getAnexos = function (idSolicitacao) {
        return get("SolicitacaoCancelamento/GetAnexos", cryptography({ Value: idSolicitacao }), true);
    };
    self.downloadAnexo = function (idSolicitacao, idDocAssociado) {
        var url = basePath.concat("Download/DownloadAnexoSolicitacaoCancelamento?param=", cryptography({ idSolicitacao, IdAnexo: idDocAssociado }));
        window.open(url, "_blank");
    };
    self.EnviarEmail = function (param) {
        return get("SolicitacaoCancelamento/EnviarEmail", cryptography(param));
    };
    self.CancelarSolicitacao = function (param) {
        return $.ajax({
            type: "GET",
            traditional: true,
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("SolicitacaoCancelamento/CancelarSolicitacao"),
            data: { param: cryptography(param) }
        });
    };
    self.exportpdf = function (param) {
        var url = basePath.concat("SolicitacaoCancelamento/Pdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
}
function RecursoGlosaRepository() {
    var self = this;

    self.pesquisar = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/Pesquisar",
            data: filtro
        });
    };
    self.pesquisarFaturas = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/PesquisarFaturasPrestador",
            data: filtro
        });
    };
    self.PesquisarFaturasByCapa = function (capa) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/PesquisarFaturasByCapa",
            data: { idcapa: capa }
        });
    };
    self.ImprimirCapa = function (capa, imprimirProtocolo, pesquisarFatura) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/ImprimirProtocolo",
            data: { capa: capa, imprimirProtocolo: imprimirProtocolo }
        });
    };
    self.countCapaEmDigitacao = function (codigoPrestador) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/CountCapaEmDigitacao",
            data: {
                codigoPrestador: codigoPrestador
            }
        });
    };
    self.getServicosComRecurso = function (capaId, pagina) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/GetServicosComRecurso",
            dataType: "json",
            contentType: "application/json",
            data: {
                idCapa: capaId,
                pagina: pagina
            }
        });
    };
    self.gerarLoteRecursoGlosa = function (codigoPrestador, fatura) {
        return $.ajax({
            type: "POST",
            async: true,
            cache: false,
            url: basePath + "RecursoGlosa/GerarLoteRecursoGlosa",
            data: {
                codigoPrestador: codigoPrestador,
                fatura: fatura
            }
        });
    };
    self.carregar = function (capa) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/Carregar",
            data: {
                id: capa
            }
        });
    };
    self.finalizarDigitacao = function (parametros) {
        return $.ajax({
            type: "POST",
            url: basePath + "RecursoGlosa/FinalizarDigitacao",
            data: parametros,
            contentType: "application/json",
            dataType: 'json'
        });
    }
    self.salvarParcialmenteDigitacao = function (parametros, async) {
        return $.ajax({
            type: "POST",
            url: basePath + "RecursoGlosa/SalvarDigitacaoParcialmente",
            data: parametros,
            async: async,
            contentType: "application/json",
            dataType: 'json'
        });
    }
    self.pesquisarServicos = function (idCapa, pagina, apenasRecursando, apenasSemJustificativa) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/PesquisarServicosLote",
            data: {
                idCapa: idCapa,
                pagina: pagina,
                apenasRecursando: apenasRecursando,
                apenasSemJustificativa, apenasSemJustificativa,
            }
        });
    };
    self.pesquisarAnexos = function (idCapa) {
        return $.ajax({
            type: "GET",
            url: basePath + "RecursoGlosa/GetAnexos",
            data: {
                chaveCapa: idCapa
            }
        });
    };
    self.removerRecursoGlosa = function (idCapa) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            cache: false,
            url: basePath + "RecursoGlosa/RemoverLoteRecursoGlosa",
            data: {
                idCapa: idCapa
            }
        });
    };
    self.saveFile = function (numeroProtocolo, fileName, pathFileName) {
        var model =
        {
            NumeroProtocolo: numeroProtocolo,
            PathFileName: pathFileName,
            FileName: fileName
        };
        var param = { param: cryptography(model) };
        return postData("RecursoGlosa/SaveFile", param)
    };
    self.downloadFile = function (idDocumento, numeroProtocolo) {
        var model =
        {
            IdDocumento: idDocumento,
            NumeroProtocolo: numeroProtocolo
        };
        window.open('/RecursoGlosa/DownloadFile?param=' + cryptography(model), '_blank', '');
    };
    self.deleteFile = function (idDocumento, numeroProtocolo) {
        var model =
        {
            IdDocumento: idDocumento,
            NumeroProtocolo: numeroProtocolo
        };
        var param = { param: cryptography(model) };
        return postData("RecursoGlosa/DeleteFile", param)
    };
}
function ConfirmarDadosBeneficiarioRepository() {
    var self = this;

    self.getCamposConfirmacaoDados = function (codigoBeneficiario) {
        return $.ajax({
            url: basePath + '/ConfirmacaoDadosBeneficiario/GetCampos',
            data: { codigoBeneficiario: codigoBeneficiario },
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    };
    self.postConfirmarDados = function (dadosConfiramcao) {
        return $.ajax({
            url: basePath + '/ConfirmacaoDadosBeneficiario/Confirmar',
            data: dadosConfiramcao,
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    };
}
function ConsultaCredenciadosRepository() {
    var self = this;

    self.pesquisar = function (filtro, isBluMed) {
        var action = "api/ConsultaCredenciados/Get";
        if (isBluMed)
            action = "api/Consulta-Credenciados-Blue-Med";

        return $.ajax({
            type: "GET",
            url: basePath + action,
            data: $.param(filtro, true),
            dataType: "json",
        });
    };
    self.salvarFavorito = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConsultaCredenciados/AdicionarFavorito",
            data: JSON.stringify(param),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            async: true
        });
    };

    self.removerFavorito = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConsultaCredenciados/RemoverFavorito",
            data: JSON.stringify(param),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            async: true
        });
    };

    self.listarFavoritos = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "ConsultaCredenciados/ListarTodosFavoritos",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            async: true
        });
    };
    self.listarTodosFavoritosBenificiarios = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "ConsultaCredenciados/ListarTodosFavoritosBeneficiario",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            async: true
        });
    };
    self.pesquisarPorFaixaCoparticipacao = function (param) {
        return get("PesquisaCoparticipacao/Get", cryptography(param));
    };
    self.searchPlanos = function (value) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/ConsultaCredenciados/SearchPlanos",
            data: { value: value },
            dataType: "json",
        });
    };
    self.pesquisarCorpoClinico = function (param) {
        return get("ConsultaCredenciados/PesquisarCorpoClinicoHospital", cryptography(param));
    };
}
function RegiaoSaudeRepository() {
    var self = this;

    self.searchRegioesSaudeByEstado = function (uf) {
        return $.ajax({
            type: "GET",
            url: basePath + "RegiaoSaude/SearchRegioesSaudeByEstado",
            data: {
                uf: uf
            },
        });
    };
}
function RegiaoRepository() {
    var self = this;

    self.SearchRegioesByCidade = function (cidade) {
        return $.ajax({
            type: "GET",
            url: basePath + "Regiao/SearchRegioesByCidade",
            data: {
                cidade: cidade
            },
        });
    };
}
function TipoAnexoGuiaRepository() {
    var self = this;

    self.get = function () {
        return $.ajax({
            type: "GET",
            url: basePath + '/File/GetAllTipoAnexoGuia',
            dataType: "json"
        });
    };
}
function SegundaViaBoletoRepository() {
    var self = this;

    self.get = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/Get"),
            data: JSON.stringify(param),
            async: true,
            dataType: "json",
            contentType: 'application/json',
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.beneficiariosNoBoleto = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/BeneficiariosNoBoleto"),
            data: JSON.stringify(param),
            async: true,
            dataType: "json",
            contentType: 'application/json',
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.detalhes = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/Detalhes"),
            data: JSON.stringify(param),
            async: true,
            dataType: "json",
            contentType: 'application/json',
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.atualizarJurosAntecipado = function (boletoId) {
        return $.ajax({
            type: "POST",
            url: basePath + "SegundaViaBoleto/atualizarJurosAntecipado",
            data: { boletoId: boletoId, },
            dataType: "json",
        });
    };
    self.boletosParaEnvioPorEmail = function (competencia, beneficiarioId) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/BoletosParaEnvioPorEmail"),
            dataType: "json",
            contentType: 'application/json',
            data: JSON.stringify({ Competencia: competencia, BeneficiarioId: beneficiarioId }),
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.listaDeAcessoPorEmail = function (competencia, beneficiarioId) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/ListaDeAcessoPorEmail"),
            data: JSON.stringify({ Competencia: competencia, Beneficiario: beneficiarioId }),
            dataType: "json",
            contentType: 'application/json',
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.gerarRelatorioBoletadasExistentes = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("SegundaViaBoleto/GerarRelatorioBoletadasExistentes"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
    self.reciboPagamento = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("SegundaViaBoleto/ReciboPagamento"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
    self.coparticipacaoBoletoCSV = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("SegundaViaBoleto/CoparticipacaoBoletoCSV"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
    self.coparticipacaoBoleto = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("SegundaViaBoleto/CoparticipacaoBoleto"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
    self.gerarExtratoMensalidadeCoParticipacao = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("SegundaViaBoleto/GerarExtratoMensalidadeCoParticipacao"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
    self.gerar2Via = function (param) {
        var url = basePath.concat("SegundaViaBoleto/Gerar2Via?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.getNotasExistentesPorBoleto = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "SegundaViaBoleto/GetNotasExistentesPorBoleto",
            data: { id: id, },
            dataType: "json",
        });
    };
    self.retornoBancario = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/RetornoBancario"),
            data: JSON.stringify(param),
            dataType: "json",
            cache: false,
            contentType: 'application/json',
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    };
    self.registrarBoletoBancarioAPI = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath + "SegundaViaBoleto/RegistrarBoleto",
            data: param,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.cancelarBoletoAPI = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath + "SegundaViaBoleto/BaixarBoleto",
            data: param,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.alterarBoletoAPI = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath + "SegundaViaBoleto/AlterarBoleto",
            data: param,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getPorEmpresa = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("SegundaViaBoleto/GetPorEmpresa"),
            data: JSON.stringify(param),
            dataType: "json",
            cache: false,
            contentType: "application/json",
            cache: false
        });
    };
}
function DemonstrativoUtilizacaoRepository() {
    var self = this;

    self.gerar = function (param) {
        return get("DemonstrativoUtilizacao/Gerar", cryptography(param));
    };

    self.visualizarPdf = function (param) {
        var url = basePath.concat("DemonstrativoUtilizacao/VisualizarPdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
}
function DemonstrativoUtilizacaoFuncespRepository() {
    var self = this;

    self.gerar = function (param) {
        return get("DemonstrativoUtilizacaoFuncesp/Gerar", cryptography(param));
    };

    self.visualizarPdf = function (param) {
        return get("DemonstrativoUtilizacaoFuncesp/VisualizarPdf", cryptography(param));
    };
}
function DemonstrativoUtilizacaoFrgRepository() {
    var self = this;

    self.gerar = function (param) {
        return get("DemonstrativoUtilizacaoFrg/Gerar", cryptography(param));
    };

    self.visualizarPdf = function (param) {
        return get("DemonstrativoUtilizacaoFrg/VisualizarPdf", cryptography(param));
    };
}

function DeclaracaoAdimplenciaRepository() {
    var self = this;

    self.email = function (solicitacao) {
        return $.ajax({
            type: "GET",
            url: basePath + "DeclaracaoAdimplencia/Email",
            data: $.param(solicitacao, true),
            dataType: "json",
        });
    };
    self.gerar = function (solicitacao) {
        return $.ajax({
            type: "GET",
            url: basePath + "DeclaracaoAdimplencia/Download",
            data: $.param(solicitacao, true),
            dataType: "json",
        });
    };
    self.getTextoPadrao = function (codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            url: basePath + "DeclaracaoAdimplencia/GetTextoPadrao",
            data: $.param({ codigoBeneficiario: codigoBeneficiario }),
            dataType: "json",
        });
    };
}
function CarenciaBeneficiarioRepository() {
    var self = this;

    self.get = function (param) {
        return get("CarenciaBeneficiario/Get", cryptography(param));
    };
    self.getCarenciasPorPrestador = function (param) {
        return get("CarenciaBeneficiario/GetCarenciasPorPrestador", cryptography(param));
    };
    self.imprimir = function (param) {
        var url = basePath.concat("CarenciaBeneficiario/ImprimirCarencias?param=", cryptography(param));
        window.open(url, "_blank");
    };
}
function HistoricoUsuarioRepository() {
    var self = this;

    self.get = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "Logon/GetHistoricosUsuario",
            data: filtro,
            dataType: "json"
        });
    };
}
function MenuRepository() {
    var self = this;

    self.getMenu = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "Logon/GetMenu",
            dataType: "json",
            async: false
        });
    };
}
function ReapresentacaoGuiaRepository() {
    var self = this;

    self.reapresentar = function (solicitacao, tipoGuia) {
        var url = self.getUrl(tipoGuia);
        return $.ajax({
            type: "POST",
            url: basePath + url,
            data: solicitacao,
            contentType: "application/json",
            dataType: 'json'
        });
    };
    self.getUrl = function (tipoGuia) {
        if (tipoGuia == 7) {
            return "ReapresentacaoGuia/ReapresentarGuiaOdontologica";
        } else if (tipoGuia == 10) {
            return "ReapresentacaoGuia/ReapresentarGuiaAnexoOPME";
        } else if (tipoGuia == 11) {
            return "ReapresentacaoGuia/ReapresentarGuiaAnexoQuimiterapia";
        } else {
            return "ReapresentacaoGuia/ReapresentarGuia";
        }
    };
}
function TrocaDeTitularidadeViewModelRepository() {
    var self = this;

    self.getBeneficiario = function (codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            async: true,
            cache: false,
            url: basePath + "TrocaTitularidade/LocalizarBeneficiario",
            data: { codigoBeneficiario: codigoBeneficiario }
        });
    }
    self.efetuarTrocaDeTitularidade = function (beneficiarios, realizarPesquisa) {
        return $.ajax({
            type: "POST",
            async: true,
            cache: false,
            url: basePath + "TrocaTitularidade/EfetuarTrocaDeTitularidade",
            data: JSON.stringify({ beneficiarios: beneficiarios, abrirPesquisaBeneficiario: realizarPesquisa }),
            contentType: "application/json",
        });
    }
}
function RelatorioDeCobrancaRepository() {
    var self = this;

    self.getDadosBeneficiario = function (codigoBeneficiario) {
        return $.ajax({
            type: "GET",
            url: basePath + "RelatorioDeCobranca/GetDadosBeneficiario?codBeneficiario=" + codigoBeneficiario,
            dataType: "json",
        });
    };
    self.solicitarcarta = function (codigoBeneficiario, datavencimento) {
        return $.ajax({
            type: "GET",
            url: basePath + "RelatorioDeCobranca/SolicitarCarta?codBeneficiario=" + codigoBeneficiario + "&datavencimento=" + datavencimento,
            //data: $.param(solicitacao, true),
            dataType: "json",
        });
    };
    self.reimprimircarta = function (codigoBeneficiario, idlote) {
        return $.ajax({
            type: "GET",
            url: basePath + "RelatorioDeCobranca/ReimprimirCarta?idLote=" + idlote + "&codBeneficiario=" + codigoBeneficiario,
            //data: $.param(solicitacao, true),
            dataType: "json",
        });
    };
    self.imprimirInadimplencia = function (codigoBeneficiario, datavencimento) {
        return $.ajax({
            type: "GET",
            url: basePath + "RelatorioDeCobranca/ImprimirInadimplencia?codBeneficiario=" + codigoBeneficiario + "&datavencimento=" + datavencimento,
            //data: $.param(solicitacao, true),
            dataType: "json",
        });
    };
}
function PlanoRepository() {
    var self = this;

    self.pesquisar = function (value) {
        return $.ajax({
            type: "GET",
            url: basePath + "Plano/Localizar",
            data: $.param({ value: value }, true),
            dataType: "json",
        });
    };
    self.pesquisarConsultaCredenciados = function (value) {
        return $.ajax({
            type: "GET",
            url: basePath + "Plano/LocalizarConsultaCredenciados",
            data: $.param({ value: value }, true),
            dataType: "json",
        });
    };
}
function AgendamentoOnlineRepository() {
    var self = this;

    self.getAgenda = function (param) {
        return get("apiAgendamentoOnline/Get", cryptography(param), false);
    };
    self.pesquisar = function (param) {
        return get("apiAgendamentoOnline/Pesquisar", cryptography(param));
    };
    self.verificarSeDeveSerRetorno = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/VerificarSeDeveSerRetorno",
            data: param,
            cache: false
        });
    };
    self.agendar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/Agendar",
            data: {
                param: cryptography(param)
            },
            cache: false,
        });
    };
    self.desmarcar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/Desmarcar",
            data: {
                param: cryptography(param)
            },
            cache: false,
        });
    };
    self.getEspecialidadesParaAgendamento = function (param) {
        return get("apiAgendamentoOnline/GetEspecialidadeParaAgendamento", cryptography(param), false);
    };
    self.verificarExistemAgendamentosFuturos = function (param) {
        return get("apiAgendamentoOnline/VerificarExistemAgendamentosFuturos", param);
    };
    self.getAgendamentosBeneficiario = function (param) {
        return get("apiAgendamentoOnline/getAgendamentosBeneficiario", cryptography(param));
    };
    self.getProtocolo = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/GetProtocolo",
            data: param,
            cache: false,
        });
    };
    self.getVersion = function () {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/GetVersion",
            data: param,
            cache: false,
        });
    };
    self.enviarProtocoloPorEmail = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "apiAgendamentoOnline/EnviarProtocoloPorEmail",
            data: {
                param: cryptography(param)
            },
            cache: false,
        });
    };
    self.gerarPDFProtocolo = function (param) {
        window.open(basePath + "apiAgendamentoOnline/GerarPDFProtocolo?BeneficiarioId=" + param.beneficiarioId + "&PrestadorId=" + param.prestadorId + "&EspecialidadeId=" + param.especialidadeId + "&Data=" + param.data + "&Horario=" + param.horario);
    };
}
//Novo Agendamento feito para Ipasgo
function AgendamentoRepository() {

    const _urlBase = "apiAgendamento";

    this.get = (url, param) => get(`${_urlBase}/${url}`, cryptography(param), true);
    this.post = (url, param) => {
        return $.ajax({
            type: "POST",
            url: `${basePath}/${_urlBase}/${url}`,
            data: {
                param: param ? cryptography(param) : null
            },
            cache: false,
        });
    }

    this.pesquisar = (param) => this.get("Pesquisar", param);
    this.verAgenda = (param) => this.get("VerAgenda", param);
    this.verAgendaTodas = (param) => this.get("VerAgendaTodas", param);
    this.agendar = (param) => this.post("Agendar", param);
    this.getAgendamentoBeneficiarioProximosDias = (param) => this.post("GetAgendamentoBeneficiarioProximosDias", param);
    this.getAgendamentosBeneficiario = (param) => this.post("GetAgendamentosBeneficiario", param);
    this.confirmarMarcacao = (param) => this.post("ConfirmarMarcacao", param);
    this.desmarcar = (param) => this.post("Desmarcar", param);
    this.confirmarPresenca = (param) => this.post("ConfirmarPresenca", param);
    this.getUrlProntuarioMedico = (param) => this.post("GetUrlProntuarioMedico", param);
    this.getUrlMarcacao = (param) => this.post("GetUrlMarcacao", param);
    this.getUrlAtendimento = (param) => this.post("GetUrlAtendimento", param);


}
function GerenciarConteudoRepository() {
    var self = this;

    self.getServicosNoticias = function (param) {
        return get("api/gerenciar-conteudo/GetServicosNoticia", param);
    };
    self.getVisualizacoesServivoNoticia = function (param) {
        return get("api/gerenciar-conteudo/GetVisualizacoesServivoNoticia", param);
    };
    self.salvarNoticia = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/gerenciar-conteudo/GravarServivoNoticia",
            data: param,
            cache: false,
        });
    };
    self.excluirNoticia = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/gerenciar-conteudo/ExcluirServivoNoticia/" + id,
            cache: false,
        });
    };
    self.getBanner = function (param) {
        return get("api/gerenciar-conteudo/GetBanners", param);
    };
    self.salvarBanner = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/gerenciar-conteudo/GravarBanner",
            data: param,
            cache: false,
        });
    };
    self.excluirBanner = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/gerenciar-conteudo/ExcluirBanner/" + id,
            cache: false,
        });
    };
}
function ConsultaCondicoesComerciaisRepository() {
    var self = this;

    self.pesquisar = function (filtro) {

        return $.ajax({
            type: "GET",
            url: basePath + "CondicoesComerciais/Get",
            data: filtro,
            contentType: "application/json",
        });
    };
}
function ProfissaoRepository() {
    var self = this;

    self.pesquisarProfissao = function (criterio) {
        return $.ajax({
            type: "POST",
            url: basePath + "Profissao/Pesquisar",
            data: { criterio: criterio },
            cache: false,
        });
    };
}
function SimularAdesaoRepository() {
    var self = this;

    self.pesquisarFaixaIdades = function (idPlano) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/simular-adesao/GetFaixaIdades",
            data: { 'idPlano': idPlano },
            dataType: "json",
        });
    };
    self.pesquisarPlanos = function (parametros) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/simular-adesao/GetPlanos",
            data: $.param(parametros),
        });
    };
    self.simular = function (parametros) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/simular-adesao/SimularWeb",
            data: JSON.stringify(parametros),
            contentType: "application/json",
            cache: false
        });
    };
    self.pesquisarAditivos = function (pagina, planoId, codSeg) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/simular-adesao/GetAditivos",
            data: {
                'pagina': pagina,
                'planoId': planoId,
                'codSeg': codSeg
            },
            dataType: "json",
        });
    };
    self.simularValoresAditivo = function (parametros) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/simular-adesao/ValoresAditivo",
            data: parametros,
            dataType: "json",
        });
    };
    self.enviarEmailNotificacaoSolicitacaoAdesaoPlano = function (dadosSolicitacaoAdesaoPlano) {
        return $.ajax({
            type: "POST",
            url: basePath + "api/simular-adesao/EnviarEmailNotificacaoSolicitacaoAdesaoPlano",
            data: dadosSolicitacaoAdesaoPlano,
            dataType: "json",
        });
    };
    self.carregarDependentes = function (codSeg) {
        return $.ajax({
            type: "GET",
            url: basePath + "api/simular-adesao/GetDependentes",
            data: { 'codSeg': codSeg }
        });
    };
}
function AvaliacaoAtendimentoRepository() {
    var self = this;

    self.enviarAvaliacao = function (viewModel) {
        return $.ajax({
            type: "POST",
            url: basePath + "AvaliacaoAtendimento/EnviarAvaliacao",
            data: viewModel,
            dataType: "json",
        });
    };
    self.pesquisarAvaliacaoes = function (viewModel) {
        return $.ajax({
            type: "GET",
            url: basePath + "AvaliacaoAtendimento/Get",
            data: viewModel,
            dataType: "json",
        });
    };
    self.getDetalhes = function (viewModel) {
        return $.ajax({
            type: "GET",
            url: basePath + "AvaliacaoAtendimento/GetDetalhes",
            data: viewModel,
            dataType: "json",
        });
    };
    self.totalizador = function (codigoPrestador) {
        return $.ajax({
            type: "GET",
            url: basePath + "AvaliacaoAtendimento/Totalizador",
            data: {
                "codigoPrestador": codigoPrestador
            },
            contentType: "application/json",
        });
    };
    self.enviarAvaliacaoProcedimento = function (viewModel) {
        return $.ajax({
            type: "POST",
            url: basePath + "AvaliacaoAtendimento/EnviarAvaliacaoProcedimento",
            data: viewModel,
            dataType: "json",
        });
    };
}
function RelatorioExtratoCoparticipacaoRepository() {
    var self = this;

    self.gerarRelatorio = function (param) {
        var url = basePath.concat("ExtratoCoparticipacao/GerarPdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.enviarEmail = function (model) {
        return get("ExtratoCoparticipacao/EnviarEmail", cryptography(model));
    }
}
function RelatorioGuiasOdontologicasPericiadasRepository() {
    var self = this;

    self.gravarFiltros = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "RelatorioGuiasOdontololicasPericiadas/SalvarFiltros",
            data: JSON.stringify(data),
            contentType: "application/json",
            cache: false
        });
    };
    self.pesquisarGuias = function (param) {
        return get("RelatorioGuiasOdontololicasPericiadas/GetViewRelatorio", param);
    };
    self.gerarRelatorio = function (param) {
        var url = basePath.concat("RelatorioGuiasOdontololicasPericiadas/Relatorio?param=", param);
        window.open(url, "_blank");
    };
}
function RelatorioExtratoSaldoAnteriorIpamRORepository() {
    var self = this;

    self.gerarRelatorio = function (codigoBeneficiario, dataInicioEmissao, dataFimEmissao) {
        window.open(basePath + "ExtratoSaldoAnteriorIpamRO/GerarPdf?codigoBeneficiario=" + codigoBeneficiario + "&dataInicioEmissao=" + dataInicioEmissao + "&dataFimEmissao=" + dataFimEmissao);
    };
}
function ConsultarDadosBeneficiarioRepository() {
    var self = this;

    self.consultar = function (param) {
        return get("ConsultarDadosBeneficiario/Consultar", cryptography(param));
    };
}
function DeclaracaoCarenciaBeneficiarioRepository() {
    var self = this;

    self.gerarPDF = function (param) {
        var url = basePath.concat("DeclaracaoCarenciaBeneficiario/GerarPDF?param=", param);
        window.open(url, "_blank");
    };
}
function AlteracaoDadosCadastraisPrestadorRepository() {
    var self = this;

    self.getSolicitacoesAlteracoes = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetSolicitacoesAlteracoes", param);
    };
    self.aprovarAlteracao = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "AlteracaoDadosCadastraisPrestador/AprovarAlteracao",
            data: { id: id }
        });
    };
    self.reprovarAlteracao = function (id, motivoId) {
        return $.ajax({
            type: "POST",
            url: basePath + "AlteracaoDadosCadastraisPrestador/ReprovarAlteracao",
            data: { id: id, motivoId: motivoId }
        });
    };
    self.getEspecialidadesPrestador = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetEspecialidadesPrestador", cryptography(param));
    };
    self.getInssRetido = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetInssRetido", cryptography(param));
    };
    self.getCorpoClinicoPrestador = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetCorpoClinicoPrestador", cryptography(param));
    };
    self.getEnderecosAtendimento = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetEnderecosAtendimento", cryptography(param));
    };
    self.getQualificacoes = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetQualificacoes", cryptography(param));
    };
    self.salvarSolicitacaoAlteracao = function (value) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "AlteracaoDadosCadastraisPrestador/SalvarAlteracoes",
            data: JSON.stringify(value),
            cache: false
        });
    };
    self.downloadArquivo = function (idCampo) {
        window.open(basePath + "Download/GetFileSolicitacaoAlteracaoDadosPrestador?idCampo=" + idCampo, '_blank', '');
    };
    self.getRegiaoCidadePorCodigoCidade = function (param) {
        return get("AlteracaoDadosCadastraisPrestador/GetRegiaoCidadePrestadorPorCodigoCidade", cryptography(param));
    }
}
function RelatorioDemonstrativoDespesasMedicasOdontologicasRepository() {
    var self = this;

    self.gerarRelatorioSintetico = function (codBeneficiario, competencia) {
        return $.ajax({
            type: "GET",
            url: basePath + "RelatorioDemonstrativoDespesasMedicasOdontologicas/gerarRelatorioSintetico",
            data: {
                codBeneficiario: codBeneficiario,
                competencia: competencia
            },
            dataType: "json",
            contentType: "application/json",
        });
    };
}
function ReceitaMedicaRepository() {
    var self = this;

    self.InserirReceita = function (receita) {
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/InserirReceita",
            data: JSON.stringify(receita),
            cache: false,
            contentType: "application/json"
        });
    };
    self.PesquisarReceitas = function (param) {
        return get("ReceitaMedica/PesquisarReceitas", param);
    };
    self.RetornarReceita = function (param) {
        return get("ReceitaMedica/RetornarReceita", cryptography(param));
    };
    self.RetornarItensReceitas = function (idsReceitas) {
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/RetornarItensReceitas",
            data: JSON.stringify({
                idsReceitas: idsReceitas
            }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.GerarGuiaReceita = function (receita) {
        if (IsUndefinedOrNullOrEmpty(receita)) { return; }
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/GerarGuiaReceita",
            data: JSON.stringify(receita),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.SalvarItemReceita = function (item) {
        if (IsUndefinedOrNullOrEmpty(item)) { return; }
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/SalvarItemReceita",
            data: JSON.stringify(item),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.SalvarValorItemReceitaMedica = function (item) {
        if (IsUndefinedOrNullOrEmpty(item)) { return; }
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/SalvarValorItem",
            data: JSON.stringify(item),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.gerarRelatorio = function (param) {
        var url = basePath.concat("ReceitaMedica/GerarPdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.gerarRelatorioJustificativa = function (idItemReceita) {
        window.open(basePath + "ReceitaMedica/GerarJustificativaPdf?idItemReceita=" + idItemReceita);
    };
    self.excluirReceita = function (IdReceita) {
        return $.ajax({
            type: "POST",
            url: basePath + "ReceitaMedica/ExcluirReceita",
            data: {
                IdReceita: IdReceita
            }
        });
    };
}
function PedidoExameRepository() {
    var self = this;

    self.InserirPedidosExame = function (pedido) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExame/InserirPedidos",
            data: JSON.stringify(pedido),
            cache: false,
            contentType: "application/json"
        });
    };
    self.PesquisarPedidos = function (param) {
        return get("PedidoExame/PesquisarPedidos", param);
    };
    self.PesquisarPedidoPorId = function (param) {
        return get("PedidoExame/PesquisarPedidoPorId", param);
    };
    self.getLogItemPedido = function (ids) {
        var model = { Value: ids };
        return get("PedidoExameGuia/GetLogItemPedido", cryptography(model));

    };
    self.GerarGuiaPedido = function (pedidoExame, arquivosExame) {
        if (IsUndefinedOrNullOrEmpty(pedidoExame)) { return; }

        var data = {
            pedido: pedidoExame,
            arquivos: arquivosExame
        };
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExame/GerarGuiaPedido",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.gerarRelatorio = function (param) {
        var url = basePath.concat("PedidoExame/GerarPdf?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.excluirPedido = function (IdPedido) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("PedidoExame/ExcluirPedido"),
            data: { IdPedido: IdPedido }
        });
    };
    self.validarPedidoRealizadoNoPeriodo = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExameGuia/ValidarPedidoRealizadoNoPeriodo",
            data: JSON.stringify(model),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.salvarPedidoExameGuia = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExameGuia/SalvarPedido",
            data: JSON.stringify(model),
            cache: false,
            dataType: "json",
            contentType: "application/json",
            timeout: 300000
        });
    };

    self.salvarPedidoExameOdonto = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExameGuia/SalvarPedidoOdonto",
            data: JSON.stringify(model),
            cache: false,
            dataType: "json",
            contentType: "application/json",
            timeout: 300000
        });
    };


    self.executarProcedimentos = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExameGuia/ExecutarPedido",
            data: JSON.stringify(model),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.cancelarProcedimentos = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "PedidoExameGuia/CancelarPedido",
            data: JSON.stringify(model),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.getPedidoExameGuia = function (model) {
        return get("PedidoExameGuia/GetPedidosExames", cryptography(model));
    };

    self.getPedidoById = function (id) {
        var model = { Value: id };
        return get("PedidoExameGuia/GetPedidoById", cryptography(model));
    };

    self.verificaProcedimentoExecutante = function (model) {
        return postData("PedidoExameGuia/VerificaProcedimentoExecutante", model, false);
    };

    self.TratarFilaRegulacao = function (guia) {
        return postData("PedidoExameGuia/TratarFilaRegulacao", guia, false);
    };

    self.getUtilizacaoSimples = function (param) {
        //var model = window.btoa(JSON.stringify(param));
        return get("PedidoExameGuia/GetUtilizacaoSimples", cryptography(param));
    };

    self.getProgramaByCodBeneficiario = function (param) {
        return get("PedidoExameGuia/GetProgramaByCodBeneficiario", param);
    };

    self.getGuiaEmProcessamento = function (item) {

        return $.ajax({
            url: basePath.concat("PedidoExameGuia/GuiaEmProcessamento"),
            data: { numeroGuiaOperadora: item.NumeroGuiaOperadora, numeroGuiaPrestador: item.NumeroGuiaPrestador },
            type: "GET",
            contentType: "application/json",
            dataType: "json",
            async: false
        });
    };
    //GetGuiaPrestadorByGuia
    self.getGuiaPrestadorByGuia = function (item) {

        return $.ajax({
            url: basePath.concat("PedidoExameGuia/GetGuiaPrestadorByGuia"),
            data: { numeroGuiaOperadora: item.NumeroGuiaOperadora, numeroGuiaPrestador: item.NumeroGuiaPrestador },
            type: "GET",
            contentType: "application/json",
            dataType: "json",
            async: false
        });
    };


}
function SolicitacaoFinanciamentoRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("SolicitacaoFinanciamento/Pesquisar", cryptography(param));
    };
    self.simular = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "SolicitacaoFinanciamento/Simular",
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.salvar = function (filtro) {
        return $.ajax({
            type: "POST",
            url: basePath + "SolicitacaoFinanciamento/Financiar",
            data: JSON.stringify(filtro),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
}
function AcompanhamentoFinanciamentoRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("AcompanhamentoFinanciamento/Pesquisar", cryptography(param));
    };
    self.relatorio = function (param) {
        var url = basePath.concat("AcompanhamentoFinanciamento/Relatorio?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.visualizarParcelas = function (filtro) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("AcompanhamentoFinanciamento/VisualizarParcelas"),
            data: JSON.stringify(filtro),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.visualizarParcelaDetalhes = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "AcompanhamentoFinanciamento/VisualizarParcelaDetalhes",
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.visualizarBoletos = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "AcompanhamentoFinanciamento/VisualizarBoletos",
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.visualizarFinanciamento = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "AcompanhamentoFinanciamento/VisualizarFinanciamento",
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.refinanciar = function (filtro) {
        return $.ajax({
            type: "POST",
            url: basePath + "AcompanhamentoFinanciamento/Refinanciar",
            data: JSON.stringify(filtro),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
}
function TetoFaturamentoRepository() {
    var self = this;

    self.search = function (param) {
        return get("GuiasTISS/TetoDeFaturamento/Search", param);
    };
}
function TetoFaturamentoVigenciaRepository() {
    var self = this;

    self.search = function (param) {
        return get("GuiasTISS/TetoDeFaturamentoVigencia/Search", param);
    };
}
function IdssRepository() {
    var self = this;

    self.gerar = function (anoBase) {
        return $.ajax({
            type: "GET",
            url: basePath + "IndicadoresIdss/Gerar?anoBase=" + anoBase,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.pesquisar = function (anoBase, id, action, idName) {

        var param = "anoBase=" + anoBase + "&" + idName + "=" + id;
        if (id != null)
            param = param + "&" + idName + "=" + id;

        return $.ajax({
            type: "GET",
            url: basePath + "IndicadoresIdss/" + action + "?" + param,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.pesquisarDimensoes = function (anoBase) {
        return self.pesquisar(anoBase, null, "PesquisarDimensoes", null);
    };
    self.pesquisarIndicadoresDimensoes = function (anoBase, id) {
        return self.pesquisar(anoBase, id, "PesquisarIndicadoresDimensoes", "idDimensao");
    };
}
function GerenciarUsuariosRepository() {
    var self = this;

    self.pesquisar = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/Pesquisar",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getUsuario = function (param) {
        return get("GerenciarUsuarios/GetUsuario", cryptography(param));
    };
    self.getPrestadoresAssociados = function (param) {
        return get("GerenciarUsuarios/GetPrestadoresAssociados", cryptography(param));
    };
    self.getBeneficiariosAssociados = function (param) {
        return get("GerenciarUsuarios/GetBeneficiariosAssociados", cryptography(param));
    };

    self.getDetalhesBeneficiarios = function (id) {
        var model = { Id: id }
        return get("GerenciarUsuarios/GetDetalhesBeneficiarios", cryptography(model));
    };
    self.save = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/Save",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.cancelarDescancelarUsuario = function (idUsuario, cancelar) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/cancelarDescancelarUsuario",
            data: JSON.stringify({ idUsuario: idUsuario, cancelar: cancelar }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.definirUsuarioComoInterno = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/DefinirUsuarioComoInterno",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.incluirPrestadorAssociado = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/IncluirPrestadorAssociado",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.excluirPrestadorAssociado = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/ExcluirPrestadorAssociado",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.incluirBeneficiarioAssociado = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/IncluirBeneficiarioAssociado",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.excluirBeneficiarioAssociado = function (data) {
        return $.ajax({
            type: "POST",
            url: basePath + "GerenciarUsuarios/ExcluirBeneficiarioAssociado",
            data: JSON.stringify(data),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
}
function InputSelectRepository() {
    var self = this;

    self.pesquisar = function (action, filter, requestType) {

        var data = {};
        var type = "GET";
        switch (action) {
            case "Plano/LocalizarConsultaCredenciados":
                data = $.param({ value: filter }, true);
                break;
            default:

                if (requestType == 2) {
                    data = JSON.stringify(filter);
                    type = "POST";
                }
                else {
                    var param = window.btoa(JSON.stringify(filter));
                    data = { param: param }

                }
                break;
        }


        return $.ajax({
            type: type,
            url: basePath + action,
            cache: false,
            data: data,
            dataType: "json",
            contentType: "application/json"
        });
    }
}
function ResultadoExamesRepository() {
    var self = this;

    self.getResultadosExames = function (param) {
        return get("ResultadoExames/GetResultadosExames", param);
    };
    self.getDadosExame = function (param) {
        return get("ResultadoExames/GetDadosExame", param);
    };
    self.salvarResultado = function (param) {
        return get("ResultadoExames/SalvarResultado", param);
    };
    self.getResultado = function (param) {
        return get("ResultadoExames/GetResultado", param);
    };
}
function AlterarEmailRepository() {
    var self = this;

    self.alterarEmail = function (novoEmail, confirmacaoEmail) {
        return $.ajax({
            type: "POST",
            url: basePath + "AlterarEmail/Alterar",
            data: {
                email: novoEmail,
                confirmacao: confirmacaoEmail
            },
            cache: false,
        });
    };
}
function LogNovoWebPlanRepository() {
    var self = this;

    self.get = function (param) {
        return get("LogNovoWebPlan/Get", param);
    };
    self.getExcpetionById = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "/LogNovoWebPlan/GetExcpetionById",
            cache: false,
            data: { Id: id },
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.gravarLog = function (type) {
        return $.ajax({
            type: "GET",
            url: basePath + "/LogNovoWebPlan/GravarLog",
            cache: false,
            data: { type: type },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getAcessosMenu = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "/LogNovoWebPlan/GetMenuAcesso",
            cache: false,
            data: { id: id },
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.getLoad = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "/LogNovoWebPlan/Load",
            cache: false,
            async: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.getCheck = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "/LogNovoWebPlan/Check",
            cache: false,
            async: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

}
function ParametroRepository() {
    var self = this;

    self.getPrametrosWebByTipo = function (idTipo) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Parametros/GetPrametrosWebByTipo",
            cache: false,
            data: { idTipo: idTipo },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.salvarWebParam = function (id, valor) {
        return $.ajax({
            type: "POST",
            url: basePath + "Parametros/SalvarParametroWeb",
            data: {
                id: id,
                valor: valor
            },
            cache: false,
        });
    };
    self.getPrametrosWebById = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "/Parametros/GetPrametrosWebById",
            cache: false,
            data: { id: id },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getTiposPrametrosWeb = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "/Parametros/GetTiposPrametrosWeb",
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
}
function ConfiguracaoDadoSensivelRepository() {
    var self = this;

    self.getConfiguracaoRelatorio = function (idRelatorio) {
        return $.ajax({
            type: "GET",
            url: basePath + "ConfiguracaoDadosSensiveis/GetConfiguracaoRelatorio",
            cache: false,
            data: { idRelatorio: idRelatorio },
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.setConfiguracaoSensivel = function (idConfiguracao, sensivel) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/SetConfiguracaoSensivel",
            data: {
                idConfiguracao: idConfiguracao,
                sensivel: sensivel
            },
            cache: false,
        });
    };
    self.alterarRestricaoPerfil = function (idConfiguracao, perfil, acao) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/AlterarRestricaoPerfil",
            data: {
                idConfiguracao: idConfiguracao,
                perfil: perfil,
                acao: acao
            },
            cache: false,
        });
    };
    self.setConfiguracaoBenefIncapaz = function (idConfiguracao, incapaz) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/SetConfiguracaoBenefIncapaz",
            data: {
                idConfiguracao: idConfiguracao,
                incapaz: incapaz
            },
            cache: false,
        });
    };
    self.setConfiguracaoBenefMaior = function (idConfiguracao, maior) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/SetConfiguracaoBenefMaior",
            data: {
                idConfiguracao: idConfiguracao,
                maior: maior
            },
            cache: false,
        });
    };
    self.setConfiguracaoBenefAgregado = function (idConfiguracao, agregado) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/SetConfiguracaoBenefAgregado",
            data: {
                idConfiguracao: idConfiguracao,
                agregado: agregado
            },
            cache: false,
        });
    };
    self.setConfiguracaoBenefDesignado = function (idConfiguracao, designado) {
        return $.ajax({
            type: "POST",
            url: basePath + "ConfiguracaoDadosSensiveis/SetConfiguracaoBenefDesignado",
            data: {
                idConfiguracao: idConfiguracao,
                designado: designado
            },
            cache: false,
        });
    };
}
function RelatorioUtilizacaoPorBeneficiarioRepository() {
    var self = this;

    self.getDados = function (param) {
        return get("RelatorioUtilizacaoPorBeneficiario/GetDados", param);
    };
}
function PreCadRepository() {
    var self = this;

    self.getArquivos = function (param) {
        return get("PreCad/GetArquivosImportados", param, true);
    };

    self.getLayoutArquivo = function (param) {
        window.open(basePath + "PreCad/GetLayoutArquivo?param=" + cryptography(param), '_blank', '');
    };
    self.getLayoutsByNome = function (nome) {
        return $.ajax({
            type: "GET",
            url: basePath + "/PreCad/GetLayoutsPorNome",
            cache: false,
            data: { nome: nome },
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.getCamposByLayoutId = function (id) {
        return $.ajax({
            type: "GET",
            url: basePath + "/PreCad/GetCamposDoLayout",
            cache: false,
            data: { id: id },
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.atualizarObrigatoriedadeCampo = function (data) {
        return $.ajax({
            type: "GET",
            url: basePath + "/PreCad/AtualizarObrigatoriedadeCampo",
            cache: false,
            data: data,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.getLinhasArquivos = function (param) {
        return get("PreCad/GetLinhasArquivosImportados", param, true);
    };
    self.getDadosLinhasArquivosImportados = function (param) {
        return get("PreCad/GetDadosLinhasArquivosImportados", param, true);
    };
    self.alteracaoEmMassa = function (param) {
        return get("PreCad/AlteracaoEmMassa", cryptography(param));
    };
    self.alteracaoEmMassaLote = function (param) {
        return postData("PreCad/AlterarDadosEmMassa", param);
    };
    self.enviarParaOperadora = function (param) {
        return get("PreCad/EnviarParaOperadora", cryptography(param));
    };
    self.getCriticasBeneficiarioLote = function (param) {
        return get("PreCad/GetCriticasBeneficiarioLote", cryptography(param), true);
    };
    self.carregarAnexosBeneficiarioLote = function (param) {
        return get("PreCad/CarregarAnexosBeneficiarioLote", cryptography(param), true);
    };
    self.getErroMessage = function (param) {
        return get("PreCad/GetErroMessage", cryptography(param), true);
    };
    self.getErrosLinhas = function (param) {
        return get("PreCad/GetErrosLinhas", param, true);
    };
    self.processarArquivo = function (param) {
        return get("PreCad/ProcessarArquivo", cryptography(param), true);
    };
    self.realizarValidacaoArquivo = function (param) {
        return get("PreCad/RealizarValidacaoArquivo", param, true);
    };
    self.excluirArquivoImportado = function (param) {
        return get("PreCad/ExcluirArquivoImportado", cryptography(param));
    };
    self.excluirLinha = function (param) {
        return get("PreCad/ExcluirLinha", param);
    };
    self.salvarAlteracaoDadosLinha = function (value) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/SalvarAlteracoes",
            data: JSON.stringify(value),
            cache: false,
            contentType: "application/json"
        });
    };
    self.getLotesDigitacao = function (param) {
        return get("PreCad/GetLotesDigitacao", param, true);
    };
    self.salvarLote = function (lote) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("PreCad/SalvarLote"),
            data: JSON.stringify(lote),
            cache: false
        });
    };
    self.salvarBeneficiarioLote = function (lote) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/SalvarBeneficiarioLote",
            data: JSON.stringify(lote),
            cache: false,
            contentType: "application/json"
        });
    };
    self.alterarSituacaoLote = function (id, aberto) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AlterarSituacaoLote",
            data: JSON.stringify({ Id: id, Aberto: aberto }),
            cache: false,
            contentType: "application/json"
        });
    };
    self.enviarLoteParaProcessamento = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/EnviarLoteParaProcessamento",
            data: JSON.stringify({ Id: id }),
            cache: false,
            contentType: "application/json"
        });
    };
    self.getBeneficiariosLote = function (param) {
        return get("PreCad/GetBeneficiariosLote", param, true);
    };
    self.getDadosBeneficiarioLote = function (param) {
        return get("PreCad/GetDadosBeneficiarioLote", cryptography(param), true);
    };
    self.getLoteDigitacaoById = function (param) {
        return get("PreCad/GetLoteDigitacaoById", cryptography(param), true);
    };
    self.loteDigitacao = function (param) {
        window.location = basePath.concat("PreCad/LoteDigitacao?param=", cryptography(param));
    };
    self.getConfiguracoesCampos = function (param) {
        return get("PreCad/GetConfiguracoesCampos", cryptography(param), true);
    };
    self.excluirLote = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/ExcluirLote",
            data: JSON.stringify({ id: id }),
            cache: false,
            contentType: "application/json"
        });
    };
    self.excluirBeneficiarioLote = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/ExcluirBeneficiarioLote",
            data: JSON.stringify({ id: id }),
            cache: false,
            contentType: "application/json"
        });
    };
    self.imprimirLote = function (param) {
        var url = basePath.concat("PreCad/ImprimirDadosLote?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.imprimirBeneficiarioLote = function (param) {
        var url = basePath.concat("PreCad/ImprimirDadosBeneficiarioLote?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.enviarArquivosLote = function (id, tipoDocumentoId, arquivos) {
        var url = basePath + "PreCad/EnviarArquivosAnexosLote";
        var data = {
            loteId: id,
            tipoDocumentoId: tipoDocumentoId,
            files: arquivos
        };

        return $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    }
    self.enviarArquivosBeneficiarioLote = function (id, beneficiarioId, tipoDocumentoId, arquivos) {
        var url = basePath + "PreCad/EnviarArquivosAnexosBeneficiarioLote";
        var data = {
            loteId: id,
            beneficiarioId: beneficiarioId,
            tipoDocumentoId: tipoDocumentoId,
            files: arquivos
        };

        return $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    }
    self.imprimirRelatorioBeneficiarios = function (param) {
        var url = basePath.concat("PreCad/ImprimirBeneficiariosArquivo?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.imprimirResumoEnvioArquivo = function (param) {
        var url = basePath.concat("PreCad/ImprimirResumoEnvioArquivo?param=", cryptography(param));
        window.open(url, "_blank");
    }
    self.removerAnexo = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/RemoverAnexo",
            data: JSON.stringify({ id: id }),
            cache: false,
            contentType: "application/json"
        });
    }
    self.enviarAnexoArquivoBeneficiario = function (arquivoId, tipoDocumentoId, arquivos) {
        var url = basePath + "PreCad/EnviarAnexoArquivoBeneficiario";
        var data = {
            arquivoId: arquivoId,
            tipoDocumentoId: tipoDocumentoId,
            files: arquivos
        };

        return $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    }
    self.enviarAnexoArquivoBeneficiarioLinha = function (arquivoId, linhaId, tipoDocumentoId, arquivos) {
        var url = basePath + "PreCad/EnviarAnexoArquivoBeneficiarioLinha";
        var data = {
            arquivoId: arquivoId,
            linhaId: linhaId,
            tipoDocumentoId: tipoDocumentoId,
            files: arquivos
        };

        return $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    }
    self.removerAnexoArquivo = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/RemoverAnexoArquivo",
            data: JSON.stringify({ id: id }),
            cache: false,
            contentType: "application/json"
        });
    }
    self.adicionarObservacaoArquivo = function (observacao, arquivoId) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AdicionarObservacaoArquivo",
            data: JSON.stringify({
                observacao: observacao,
                arquivoId: arquivoId
            }),
            cache: false,
            contentType: "application/json"
        });
    }
    self.adicionarObservacaoArquivoLinha = function (observacao, cod_linha) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AdicionarObservacaoArquivoLinha",
            data: JSON.stringify({
                observacao: observacao,
                cod_linha: cod_linha
            }),
            cache: false,
            contentType: "application/json"
        });
    }
    self.adicionarObservacaoCadastramentoBeneficiario = function (observacao, chave) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AdicionarObservacaoCadastramentoBeneficiario",
            data: JSON.stringify({
                observacao: observacao,
                chave: chave
            }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.adicionarObservacaoCadastramentoLote = function (observacao, cod_cadlote) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AdicionarObservacaoCadastramentoLote",
            data: JSON.stringify({
                observacao: observacao,
                cod_cadlote: cod_cadlote
            }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    }
    self.getObservacaoByArquivo = function (param) {
        return get("PreCad/GetObservacaoByArquivo", cryptography(param), true);
    };
    self.getObservacaoByArquivoLinha = function (param) {
        return get("PreCad/GetObservacaoByArquivoLinha", cryptography(param), true);
    };
    self.getObservacaoByCadastramentoLote = function (param) {
        return get("PreCad/GetObservacaoByCadastramentoLote", cryptography(param), true);
    };
    self.getObservacaoByCadastramentoBeneficiario = function (param) {
        return get("PreCad/GetObservacaoByCadastramentoBeneficiario", cryptography(param), true);
    };
    self.adicionarObservacaoRecusarArquivo = function (observacao, arquivoId) {
        return $.ajax({
            type: "POST",
            url: basePath + "PreCad/AdicionarObservacaoRecusarArquivo",
            data: JSON.stringify({
                observacao: observacao,
                arquivoId: arquivoId
            }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.adicionarObservacaoRecusarLote = function (observacao, loteId) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("PreCad/AdicionarObservacaoRecusarLote"),
            data: JSON.stringify({
                observacao: observacao,
                loteId: loteId
            }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.resolverPendenciaLinha = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("PreCad/ResolverPendenciaLinha"),
            data: JSON.stringify({ id: id }),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.resolverPendenciaBeneficiario = function (param) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("PreCad/ResolverPendenciaBeneficiario"),
            data: { param: cryptography(param) },
            cache: false,
            async: false
        });
    };
    self.carregarAnexosLote = function (param) {
        return get("PreCad/CarregarAnexosLote", cryptography(param), true);
    };
    self.carregarAnexosArquivoLinha = function (param) {
        return get("PreCad/CarregarAnexosArquivoLinha", cryptography(param), true);
    };
    self.carregarAnexosArquivo = function (param) {
        return get("PreCad/CarregarAnexosArquivo", cryptography(param), true);
    };
}
function AuditoriaRetrospectivaRepository() {
    var self = this;

    self.getLotes = function (param) {
        return get("AuditoriaRetrospectiva/GetLotes", cryptography(param));
    };
    self.getDetalhesLotes = function (param) {
        return get("AuditoriaRetrospectiva/GetDetalhesLotes", cryptography(param));
    };
    self.getItensLoteByBeneficiarioTipo = function (param) {
        return get("AuditoriaRetrospectiva/GetItensLoteByBeneficiarioTipo", param);
    };
    self.getAnexos = function (param) {
        return get("AuditoriaRetrospectiva/GetAnexos", cryptography(param));
    };
    self.pesquisarXmls = function (param) {
        return get("AuditoriaRetrospectiva/GetXmlTiss", param);
    };
    self.confirmarDesconfirmarItemLote = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "AuditoriaRetrospectiva/ConfirmarDesconfirmarItemLote",
            data: JSON.stringify({ param: param }),
            dataType: "json",
            contentType: "application/json",
            cache: false,
        });
    };
    self.gerarLote = function (xmlTissId) {
        return $.ajax({
            type: "POST",
            url: basePath + "AuditoriaRetrospectiva/GerarLote",
            data: JSON.stringify({ xmlTissId: xmlTissId }),
            dataType: "json",
            contentType: "application/json",
            cache: false,
        });
    };
    self.enviarArquivos = function (loteId, arquivos) {
        var data = {
            loteId: loteId,
            files: arquivos
        };

        return $.ajax({
            type: "POST",
            url: basePath + "AuditoriaRetrospectiva/EnviarAnexos",
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            cache: false,
        });
    };
    self.aprovarLote = function (loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "AuditoriaRetrospectiva/AprovarLote",
            data: JSON.stringify({ loteId: loteId }),
            dataType: "json",
            contentType: "application/json",
            cache: false,
        });
    };
    self.devolverLote = function (loteId) {
        return $.ajax({
            type: "POST",
            url: basePath + "AuditoriaRetrospectiva/DevolverLote",
            data: JSON.stringify({ loteId: loteId }),
            dataType: "json",
            contentType: "application/json",
            cache: false,
        });
    };
    self.obterPareceresPorCodigoItem = function (param) {
        return get("AuditoriaRetrospectiva/ObterPareceresPorCodigoDoItem", cryptography(param));
    };
    self.obterGruposPorBeneficiarioELote = function (param) {
        return get("AuditoriaRetrospectiva/ObterGruposPorBeneficiarioELote", cryptography(param));
    };
}
function TermoConsentimentoRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("TermoConsentimento/Pesquisar", param);
    };
    self.desativar = function (param) {
        return get("TermoConsentimento/Desativar", cryptography(param));
    };
    self.solicitarConsentimento = function (param) {
        return get("TermoConsentimento/SolicitarConsentimento", cryptography(param));
    };
    self.salvarTermo = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "TermoConsentimento/SalvarTermo",
            data: JSON.stringify(model),
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.viewReportAceite = function (param) {
        window.open(basePath + "TermoConsentimento/ViewReportAceite?param=" + param);
    };
    self.getTermoUsuario = function () {

        return $.ajax({
            type: "GET",
            url: basePath + "TermoConsentimento/GetTermoUsuario",
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.darAceite = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "TermoConsentimento/DarAceite",
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.fecharModalAceite = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "TermoConsentimento/FecharModalAceite",
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
    self.getTermo = function (param) {
        return get("TermoConsentimento/GetTermo", cryptography(param));
    };
    self.getInfoAceiteTermoAtivo = function () {
        return getWithoutParam("TermoConsentimento/GetInfoAceiteTermoAtivo");
    };
}
function DossieRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("Dossie/Pesquisar", param);
    };
    self.alterarStatus = function (param) {
        return get("Dossie/AlterarStatus", cryptography(param));
    };
    self.salvar = function (model) {
        return $.ajax({
            type: "POST",
            url: basePath + "Dossie/Salvar",
            data: JSON.stringify(model),
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.getDossie = function (param) {
        return get("Dossie/GetDossie", cryptography(param));
    };
    self.salvarAssinatura = function (file) {
        var formData = new FormData();
        formData.append("file", file);
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Dossie/UploadAssinatura"),
            data: formData,
            contentType: false,
            processData: false,
        });
    };
    self.imprimir = function (param) {
        window.open(basePath + "Dossie/Imprimir?param=" + param);
    };
}
function PedidoAlteracaoCadastralEmpresaRepository() {
    var self = this;

    self.pesquisar = function (param) {
        return get("PedidoAlteracaoCadastralEmpresa/Pesquisar", param);
    };
    self.AprovarAlteracao = function (id) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("PedidoAlteracaoCadastralEmpresa/AprovarAlteracao"),
            data: {
                id: id
            }
        });
    };
    self.ReprovarAlteracao = function (id) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("PedidoAlteracaoCadastralEmpresa/ReprovarAlteracao"),
            data: {
                id: id
            }
        });
    };
    self.AprovarTodos = function (param) {
        return get("PedidoAlteracaoCadastralEmpresa/AprovarTodos", param);
    };
    self.ReprovarTodos = function (param) {
        return get("PedidoAlteracaoCadastralEmpresa/ReprovarTodos", param);
    };
    self.ExportarDados = function (param) {
        var url = basePath.concat("PedidoAlteracaoCadastralEmpresa/ExportarAlteracoesEmpresa?param=", param);
        window.open(url, "_blank");
    };
    self.EmailAlteracaoReprovada = function (param) {
        return get("PedidoAlteracaoCadastralEmpresa/EmailAlteracaoReprovada", param);
    };
    self.GetEmailAlteracaoReprovada = function (param) {
        return get("PedidoAlteracaoCadastralEmpresa/GetEmailAlteracaoReprovada", param);
    };
}
function VacinacaoRepository() {
    var self = this;

    self.detalharLote = function (param) {
        window.location = "ViewAplicacaoVacina?param=".concat(cryptography(param));
    };
    self.consultarVacinadosLote = function (param) {
        window.location = "ViewConsultaVacinados?param=".concat(cryptography(param));
    };
    self.guiaAtendimentoVacinacao = function (param) {
        var url = basePath.concat("Relatorios/ViewGuiaAtendimentoVacinacao?param=", cryptography(param));
        window.open(url, "_blank");
    };
    self.relatorioVacinadosPorLote = function (param) {
        var url = basePath.concat("Relatorios/ViewRelatorioVacinadosPorLote?param=", cryptography(param));
        window.open(url, "_blank");
    };
}
function UploadRepository() {
    var self = this;

    self.deleteFile = function (fileName) {
        return $.ajax({
            type: "POST",
            //dataType: "json",
            //contentType: "application/json",
            url: basePath.concat("Upload/DeleteFile"),
            data: {
                fileName: fileName
            },
            async: false,
            cache: false
        });
    };

    self.tempFile = function (fileName) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Upload/TempFile"),
            data: {
                fileName: fileName
            },
            async: false,
            cache: false
        });
    };

    self.sendFile = function (file, uniqueTempFolderId) {

        var data = new FormData();
        data.append('file', file);

        if (!IsUndefinedOrNullOrEmpty(uniqueTempFolderId))
            data.append('uniqueTempFolderId', uniqueTempFolderId);

        return $.ajax({
            url: basePath.concat("Upload/SendFile"),
            data: data,
            method: "POST",
            cache: false,
            processData: false,
            contentType: false,
        });
    }

}
function ProtocoloPropostaRepository() {
    var self = this;

    self.consultar = function (filtro) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ProtocoloProposta/Consultar"),
            data: filtro
        });
    };
    self.salvar = function (data) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ProtocoloProposta/Salvar"),
            data: data
        });
    };
    self.removerAnexo = function (id) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ProtocoloProposta/RemoverAnexo"),
            data: JSON.stringify({
                id: id
            }),
            cache: false
        });
    };
    self.consultarBeneficiario = function (cpf) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ProtocoloProposta/ConsultarBeneficiario"),
            data: {
                cpf: cpf
            },
            cache: false
        });
    };
    self.consultarEmpresa = function (cnpj) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ProtocoloProposta/ConsultarEmpresa"),
            data: {
                cnpj: cnpj
            },
            cache: false
        });
    };
}
function LocalizarProcedimentosRepository() {
    var self = this;

    self.getHistoricoObservacao = function (param) {
        return get("LocalizarProcedimentos/GetHistoricoObservacao", cryptography(param));
    };
    self.alertarBeneficiarioCancelado = function (param) {
        return get("Relatorios/AlertarBeneficiarioCancelado", cryptography(param));
    };

    self.getHistoricoPedidoExames = function (idPedido) {
        var model = { Value: idPedido };
        return get("LocalizarProcedimentos/GetHistoricoPedidoExames", cryptography(model));
    };

    self.podeAdicionarDadosNaGuiaRequest = function (item) {
        return $.ajax({
            url: basePath + 'LocalizarProcedimentos/GetGuiaEstaNaEtapaFinalDoRegulacao',
            data: { numeroGuiaOperadora: item.NumeroGuiaOperadora, numeroGuiaPrestador: item.NumeroGuiaPrestador },
            type: "POST",
            dataType: "json",
            async: false
        });
    };

    self.getAllFiles = function (item) {
        return $.ajax({
            url: basePath + 'File/GetAllFiles',
            data: { numeroGuiaOperadora: item.NumeroGuiaOperadora, numeroGuiaPrestador: item.NumeroGuiaPrestador },
            type: "GET",
            dataType: "json"
        })
    }

    self.sendFile = function (formData) {
        return $.ajax({
            type: "POST",
            url: basePath + 'Upload/Send',
            data: formData,
            cache: false,
            contentType: false,
            processData: false
        });
    }

    self.cancelar = function (pedido) {
        return $.ajax({
            url: basePath.concat('LocalizarProcedimentos/Cancelar'),
            data: { CodigoSolicitante: pedido.SolicitanteID, NumeroGuiaOperadora: pedido.NumeroGuiaOperadora, NumeroGuiaPrestador: pedido.NumeroGuiaPrestador, PedidoId: pedido.PedidoId },
            type: "POST",
            dataType: "json"
        });
    }

    self.saveObs = function (item) {
        return $.ajax({
            url: basePath + 'LocalizarProcedimentos/AddHistoricoObservacao',
            data: item,
            type: "POST",
            dataType: "json",
            contentType: 'application/json',
            cache: false
        });
    }

    self.removerAnexo = function (item) {
        return $.ajax({
            url: basePath + 'File/Delete',
            data: { id: item.Nome, searchBySolicitante: true },
            type: "POST",
            dataType: "json"
        });
    }
}
function EmailBoasVindasRepository() {
    var self = this;

    self.consultar = function (param) {
        return get("EmailBoasVindas/Consultar", cryptography(param));
    };
    self.solicitar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "EmailBoasVindas/Solicitar",
            data: param,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.remover = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "EmailBoasVindas/Remover",
            data: id,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
}
function TemplateHtmlRepository() {
    var self = this;

    self.consultar = function (param) {
        return get("TemplateHtml/Consultar", cryptography(param));
    };
    self.solicitar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateHtml/Solicitar",
            data: param,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.remover = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateHtml/Remover",
            data: id,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.removerFiltro = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateHtml/RemoverFiltro",
            data: id,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };

    self.getVariaveis = function (templateTipoId) {
        return get("TemplateHtml/GetVariaveis", templateTipoId);
    };
}
function TemplateTipoRepository() {
    var self = this;

    self.consultar = function (param) {
        return get("TemplateTipo/Consultar", cryptography(param));
    };
    self.adicionar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateTipo/Adicionar",
            data: param,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.remover = function (id) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateTipo/Remover",
            data: id,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
    self.salvar = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath + "TemplateTipo/Salvar",
            data: param,
            cache: false,
            contentType: "application/json;charset=utf-8"
        });
    };
}
function LogonRepository() {
    var self = this;

    self.validarPergunta = function (param, doneCallback) {
        return get("Logon/ValidarPergunta", cryptography(param), false)
            .done(doneCallback);
    };
    self.validarLoginExistente = function (param, doneCallback) {
        return get("Logon/ValidarLoginExistente", cryptography(param), true)
            .done(doneCallback);
    };
    self.validarLoginNaoAtivado = function (param, doneCallback) {
        return get("Logon/ValidarLoginNaoAtivado", cryptography(param), true)
            .done(doneCallback);
    };
    self.validarNumeroCarteiraOrCodSegOrCpfOrCnpj = function (param, doneCallback) {
        return get("Logon/ValidarNumeroCarteiraOrCodSegOrCpfOrCnpj", cryptography(param), false)
            .done(doneCallback);
    };
    self.carregarPerguntas = function (param, doneCallback) {
        return get("Logon/CarregarPerguntas", cryptography(param))
            .done(doneCallback);
    };
    self.carregarContasEmail = function (param, doneCallback) {
        return get("Logon/CarregarContasEmail", cryptography(param))
            .done(doneCallback);
    };
    self.carregarContasLogins = function (param, doneCallback) {
        return get("Logon/CarregarContasLogins", cryptography(param))
            .done(doneCallback);
    };
    self.carregarTiposDeAcesso = function (doneCallback) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Logon/CarregarTiposDeAcesso"),
            cache: false,
            async: false
        }).done(doneCallback);
    };
    self.validarUsuarioEmUso = function (param, doneCallback) {
        return get("Logon/ValidarUsuarioEmUso", cryptography(param))
            .done(doneCallback);
    };
    self.criarConta = function (param, doneCallback) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/CriarConta"),
            data: {
                param: cryptography(param)
            },
            cache: false,
        }).done(doneCallback);
    };
    self.atualizarConta = function (param, doneCallback) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/AtualizarConta"),
            data: {
                param: cryptography(param)
            },
            cache: false,
        }).done(doneCallback);
    };
    self.recuperarSenha = function (param, doneCallback) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/RecuperarSenha"),
            data: {
                param: cryptography(param)
            },
            cache: false,
        }).done(doneCallback);
    };
    self.reenviarCodigoEmail = function (param, doneCallback) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/ReenviarCodigoEmail"),
            data: {
                param: cryptography(param)
            },
            cache: false
        }).done(doneCallback);
    };
    self.abrirLinkAutenticacao = function (param) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/AbrirLinkAcesso"),
            data: {
                param: cryptography(param)
            },
            cache: false,
            success: function (data) {
                window.open(window.URL.createObjectURL(new Blob([new Uint8Array(data)], { type: "application/pdf" })), "_blank");
            }
        });
    };
    self.redirecionarPrimeiroAcesso = function (param) {
        var url = basePath.concat("Logon/PrimeiroAcesso?param=", cryptography(param));
        window.open(url, "_self");
    };
    self.redirecionarRecuperarSenha = function (param) {
        var url = basePath.concat("Logon/RecuperarAcesso?param=", cryptography(param));
        window.open(url, "_self");
    };
    self.exibirAvisoPosLogon = function (doneCallback) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Logon/GetAvisosPosLogon"),
            cache: false,
            async: false
        }).done(doneCallback);
    };
    self.leituraAvisoPosLogon = function (param, doneCallback) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: basePath.concat("Logon/LeituraAvisoPosLogon"),
            data: { param: cryptography(param) },
            cache: false,
            async: false
        }).done(doneCallback);
    };
    self.getArquivoPDFAvisoLogin = function (param) {
        window.open(basePath + "Logon/GetArquivoPDFAvisoLogin?param=" + cryptography(param), '_blank', '');
    };
}
function SaldoTetoReembolsoRepository() {
    var self = this;

    self.consultarSaldoBenef = function (param) {
        return get("SaldoTetoReembolso/ConsultarSaldoBeneficiario", cryptography(param));
    };
}
function ExtratoProcedimentoRepository() {
    var self = this;

    self.gerarPdf = function (model) {
        var url = basePath.concat("ExtratoProcedimento/GerarRelatorio?param=", cryptography(model));
        window.open(url, "_blank");
    };

    self.get = function (model) {
        return get("ExtratoProcedimento/GetItens", cryptography(model));
    };
}
function PrescricaoMedicaRepository() {
    var self = this;

    self.get = function (param) {
        return get("PrescricaoMedica/GetPrescricoes", cryptography(param));
    };

    self.getProcedimentosPrescricao = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetProcedimentosPrescricao", cryptography(param));
    };

    self.getObservacaoProcedimentoPrescricoes = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetObservacaoProcedimentoPrescricao", cryptography(param));
    };

    self.getObservacoesPrescricaoMedica = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetObservacoesPrescricaoMedica", cryptography(param));
    };

    self.adicionarObservacaoPrescricaoMedica = function (data) {
        return postData("PrescricaoMedica/AdicionarObservacaoPrescricaoMedica", data);
    };

    self.adicionarPrescricao = function (data) {
        return postData("PrescricaoMedica/SalvarPrescricao", data);
    };

    self.editarDataValidade = function (data) {
        return postData("PrescricaoMedica/EditarDataValidade", data);
    }

    self.editarQuantidadeAutorizada = function (data) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "PrescricaoMedica/EditarQuantidadeAutorizada",
            data: JSON.stringify({ 'param': cryptography(data) }),
            cache: false
        });

    }
    self.enviarEmailBeneficiario = function (data) {
        return get("PrescricaoMedica/EnviarEmailPrescricaoMedicaBeneficiario", cryptography(data));
    }

    self.getAtualizaStatusPrescricaoMedica = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetAtualizaStatusPrescricaoMedica", cryptography(param));
    };

    self.getObtemSituacaoPrescricaoMedica = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetObtemSituacaoPrescricaoMedicaByItemPrescricao", cryptography(param));
    };

    self.getBeneficiarioPossuiAditivo = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/BeneficiarioPossuiAditivos", cryptography(param));
    };

    self.alteraSituacaoProcedimentoPrescricao = function (data) {
        return postData("PrescricaoMedica/AlteraSituacaoProcedimentoPrescricao", data);
    };

    self.adicionarProcedimentoPrescricao = function (data) {
        return postData("PrescricaoMedica/AdicionarProcedimentoPrescricao", data);
    };

    self.getFilesPrescricao = function (id) {
        var param = { Value: id };
        return get("PrescricaoMedica/GetFilesPrescricao", cryptography(param));
    };

    self.excluirFile = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("PrescricaoMedica/ExcluirFile", param);
    };

    self.adicionarFile = function (id, files) {
        var model =
        {
            IdPrescricao: id,
            Files: files
        };
        return postData("PrescricaoMedica/AdicionarFile", model);
    };

    self.excluirPrescricaoMedica = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("PrescricaoMedica/ExcluirPrescricaoMedica", param);
    };

    self.verificaSePodeImprimirCartaNegativa = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };
        return postData("PrescricaoMedica/VerificaSePodeImprimirCartaNegativa", param);
    };

    self.imprimirCartaDeNegativa = function (id) {
        var model = { Value: id };
        var url = basePath.concat("PrescricaoMedica/ImprimirCartaDeNegativa?param=", cryptography(model));
        window.open(url, "_blank");
    }
}
function ParcelamentoDeDebitosRepository() {
    var self = this;

    self.getParcelamentosDoBeneficiario = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitos/ObterParcelamentosBeneficiario", cryptography(param));
    }

    self.getBoletosPassiveisDeFinanciamento = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitos/ObterBoletosPassiveisDeFinanciamento", cryptography(param));
    }

    self.getSimulacaoParcelas = function (objetoParcelaEListaBoletos) {
        return get("ParcelamentoDebitos/ObterSimulacaoParcelas", cryptography(objetoParcelaEListaBoletos));
    }

    self.getParametrosParcelamento = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitos/ObterRestricoesParcelamento", cryptography(param));
    }

    self.salvarParcelamento = function (objetoParcelaEListaBoletos) {
        var model = { param: cryptography(objetoParcelaEListaBoletos) };
        return postData("ParcelamentoDebitos/SalvarParcelamento", model);
    }

    self.RemoverSimulacao = function (IdTabelaTemporaria) {
        var model = { param: cryptography({ Id: IdTabelaTemporaria }) };
        return postData("ParcelamentoDebitos/RemoverSimulacao", model);
    }

    self.getFormasPagamentosValidas = function (codBeneficiario) {
        var model = { param: cryptography({ CodigoBeneficiario: codBeneficiario }) };
        return postData("ParcelamentoDebitos/ObterFormasPagamentosValidas", model);
    }

}
function ParcelamentoDeDebitosFuncespRepository() {
    var self = this;

    self.getParcelamentosDoBeneficiario = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitosFuncesp/ObterParcelamentosBeneficiario", cryptography(param));
    }

    self.getBoletosPassiveisDeFinanciamento = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitosFuncesp/ObterBoletosPassiveisDeFinanciamento", cryptography(param));
    }

    self.getSimulacaoParcelas = function (objetoParcelaEListaBoletos) {
        return get("ParcelamentoDebitosFuncesp/ObterSimulacaoParcelas", cryptography(objetoParcelaEListaBoletos));
    }

    self.getParametrosParcelamento = function (codBeneficiario) {
        var param = { CodigoBeneficiario: codBeneficiario };
        return get("ParcelamentoDebitosFuncesp/ObterRestricoesParcelamento", cryptography(param));
    }

    self.salvarParcelamento = function (objetoParcelaEListaBoletos) {
        var model = { param: cryptography(objetoParcelaEListaBoletos) };
        return postData("ParcelamentoDebitosFuncesp/SalvarParcelamento", model);
    }

    self.RemoverSimulacao = function (IdTabelaTemporaria) {
        var model = { param: cryptography({ Id: IdTabelaTemporaria }) };
        return postData("ParcelamentoDebitosFuncesp/RemoverSimulacao", model);
    }

    self.getFormasPagamentosValidas = function (codBeneficiario) {
        var model = { param: cryptography({ CodigoBeneficiario: codBeneficiario }) };
        return postData("ParcelamentoDebitosFuncesp/ObterFormasPagamentosValidas", model);
    }

}
function EnvioXmlItegradoRepository() {
    var self = this;

    self.get = function (model) {
        return get("RecebeXMLIntegradoTISS/GetXmls", cryptography(model));
    }

    self.imprimirProtocolo = function (id) {
        var model = { Value: id };
        return get("RecebeXMLIntegradoTISS/ImprimirProtocolo", cryptography(model));
    }

    self.getErro = function (id) {
        var model = { Value: id };
        return get("RecebeXMLIntegradoTISS/GetErro", cryptography(model));
    }

    self.download = function (id, tipoXml) {
        var param = { Id: id, Tipo: tipoXml }
        var url = basePath.concat("RecebeXMLIntegradoTISS/Download?param=", cryptography(param));
        window.open(url, "_blank");
    }


}
function SaldoDevedorRepository() {
    var self = this;

    self.getTitular = function (model) {
        return get("RelatorioSaldoDevedorBeneficiario/ConsultaGrupoFamiliarBeneficiario", cryptography(model));
    }
}
function EnvioEmailRepository() {
    var self = this;

    self.enviarEmailExtratoIRPFAnual = function (model) {
        return get("Relatorios/EnviarEmailExtratoBeneficiarioIRPFAnual", cryptography(model));
    }
    self.enviarEmailRelatorioContribuicao = function (model) {
        return get("Relatorios/EnviarEmailRelatorioContribuicao", cryptography(model));
    }
    self.enviarEmailRelatorioAnualIRPdf = function (model) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("/IRBeneficiario/EnviarEmailRelatorioAnualIRPdf"),
            data: JSON.stringify(model),
            cache: false,
        });
    }

    self.enviarEmailExtratoDespesasReembolso = function (model) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("ExtratoDespesasReembolsos/Gerar"),
            data: JSON.stringify(model),
            cache: false,
        });
    }

    self.enviarEmailRelatorioImpostoPagoPdf = function (model) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("IRBeneficiario/RelatorioImpostoPagoPdf"),
            data: JSON.stringify(model),
            cache: false,
        });
    }

    self.enviarEmailRelatorioAnualIR = function (model) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("IR/RelatorioAnualIRPdf"),
            data: JSON.stringify(model),
            cache: false,
        });
    }
}
function IntegracaoBeneficiariosRepository() {
    var self = this;

    self.getBeneficiarios = function (param) {
        return get("Integracao/GetBeneficiarios", cryptography(param))
    }

    self.mostrarInconsistencias = function (param) {
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Integracao/GetInconistenciasArquivo"),
            data: JSON.stringify({ filter: param }),
            cache: false,
        });
    }

    this.DownloadCsvDivergenciasIntegracaoBenefFacplanXTxt = async function (param) {
        try {
            
            const response = await fetch('/Integracao/DownloadCsvDivergencias', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ filter: param })
            });

            if (!response.ok) throw new Error("Erro ao gerar o arquivo");            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');            
            a.href = url;
            a.download = "Inconsistencias_dados.csv";
            
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error("Falha no download:", error);
            alert("Erro ao baixar o arquivo.");
        }
    }


    self.getDetalheBeneficiario = function (param) {
        return get("Integracao/GetDetalheBeneficiario", cryptography(param))
    }

    self.getregistrosAgrupadosPorErro = function (param) {
        return get("Integracao/GetRegistrosAgrupadosPorErro", cryptography(param))
    }

    self.getRegistrosAgrupadosPorErroByMensagem = function (param, actionName) {
        return get("Integracao/GetRegistrosPorErroByMensagem", cryptography(param))
    }

    self.getLinhasNaoImportadas = function (param) {
        return get("Integracao/GetLinhasNaoImportadas", cryptography(param))
    }

    self.getConteudoLinhas = function (id) {
        var model = { Value: id };
        return get("Integracao/GetConteudoLinhas", cryptography(model))
    }

    self.getInformacoesControleImportacao = function (id) {
        var model = { Value: id };
        return get("Integracao/GetInformacoesControleImportacao", cryptography(model))
    }

    self.reprocessarBeneficiarioIntegracao = function (beneficiario) {
        var model = { Value: beneficiario.codigo() };
        return get("Integracao/ReprocessarBeneficiarioIntegracao", cryptography(model))
    }



    self.getPrestadores = function (param) {
        return get("Integracao/GetPrestadores", cryptography(param))
    }

    self.getDetalhesPrestadores = function (param) {
        return get("Integracao/GetDetalhePrestadores", cryptography(param))
    }

    self.getEnderecoAtendimentoPrestador = function (param) {
        return get("Integracao/GetEnderecoAtendimentoPrestador", cryptography(param))
    }

    self.getEspecialidadesPrestador = function (param) {
        return get("Integracao/GetEspecialidadesPrestador", cryptography(param))
    }

    self.getCorpoClinicoPrestador = function (param) {
        return get("Integracao/GetCorpoClinico", cryptography(param))
    }

    self.getBeneficiariosFrg = function (param) {
        return get("Integracao/GetBeneficiariosFrg", cryptography(param))
    }

    self.getDetalheBeneficiarioFrg = function (param) {
        return get("Integracao/GetDetalheBeneficiarioFrg", cryptography(param))
    }

    //Integração de Proposta
    self.listarBeneficiariosEnviados = function (param) {
        return get("Integracao/ListarBeneficiariosEnviados", cryptography(param))
    }

    self.exportarBeneficiarios = function (param) {
        var url = basePath.concat("Integracao/ExportarBeneficiarios?param=", cryptography(param));
        window.open(url, "_blank");
    }

    self.getBeneficiarioIntegracaoProposta = function (param) {
        return get("Integracao/GetBeneficiarioIntegracaoProposta", cryptography(param));
    }
}


function IntegracaoFolhaRepository() {
    var self = this;

    self.getBeneficiariosFolha = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Integracao/GetBeneficiariosFolha"),
            data: param,
            cache: false,
        });
    }

    self.getConfiguracaoIntegracaoFolha = function () {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("Integracao/GetConfiguracaoIntegracaoFolha"),
            data: null,
            cache: false
        });
    };

    self.getTemArquivoProcessado = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetTemArquivoProcessado"),
            data: param,
            cache: false
        });
    };

    self.getPodeEnviarArquivo = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetPodeEnviarArquivo"),
            data: param,
            cache: false
        });
    };

    self.salvarArquivosNoDiretorio = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("Integracao/SalvarArquivosNoDiretorio"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    }

    self.getDadosAcoesBeneficiarioFolha = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetDadosAcoesBeneficiarioFolha"),
            data: param,
            cache: false
        });
    };

    self.getDetalheBeneficiarioFolha = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetDetalheBeneficiarioFolha"),
            data: param,
            cache: false
        });
    };

    self.getDependentes = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetDependentes"),
            data: param,
            cache: false
        });
    };

    self.getVerbaDadosFinanceiros = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetVerbaDadosFinanceiros"),
            data: param,
            cache: false
        });
    };

    self.getCalculoDadosFinanceiros = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetCalculoDadosFinanceiros"),
            data: param,
            cache: false
        });
    };

    self.getAlertasFolha = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetAlertasFolha"),
            data: param,
            cache: false
        });
    };

    self.getTotalizadoresFolha = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GetTotalizadoresFolha"),
            data: param,
            cache: false
        });
    };    

    self.processarFolhaWeb = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("Integracao/ProcessarFolhaWeb"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    }

    self.finalizarFolhaWeb = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("Integracao/FinalizarFolhaWeb"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    }

    self.gerarRelatorioResumo = function (param) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            url: basePath.concat("Integracao/GerarRelatorioResumo"),
            data: param,
            cache: false
        });
    };

    self.gerarRelatorioPatrocinio = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarFolhaPatrocinio?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.gerarRelatorioLicencas = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarFolhaLicenca?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.gerarRelatorioSituacao = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarFolhaSituacao?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.exportarFolhaCSV = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/ExportarFolhaBeneficiarioCsv?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.exportarPlanilhaCSV = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/ExportarPlanilhaBeneficiarioCsv?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.gravarAcao = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("Integracao/GravarAcao"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };

    self.desfazerAcao = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("Integracao/DesfazerAcao"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
}


function RelatoriosAnaliticosRepository() {
    var self = this;

    self.getExecucoes = function (param) {
        return get("RelatoriosAnaliticos/GetExecucoesRelatorio", cryptography(param))
    }

    self.getInformacoesGeradas = function (param) {
        return get("RelatoriosAnaliticos/GetInformacoesGeradas", cryptography(param))
    }

    self.getCamposByLinha = function (param) {
        return get("RelatoriosAnaliticos/GetCamposByLinha", cryptography(param))
    }

    self.getRelatorio = function (param) {
        return get("RelatoriosAnaliticos/GetRelatorio", cryptography(param))
    }

    self.salvar = function (model) {
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/SalvarRelatorio", param, true);
    };

    self.send = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/Send", param, true);
    };

    self.alterarVisibilidadeWeb = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/AlterarVisibilidadeWeb", param, true);
    };

    self.alterarSobrecrever = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/AlterarSobrecrever", param, true);
    };

    self.alterarExibirHeader = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/AlterarExibirHeader", param, true);
    };

    self.exibirFieldWeb = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/ExibirFieldWeb", param, true);
    };

    self.alterarStatus = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/AlterarStatus", param, true);
    };

    self.executarRelatorio = function (model) {
        var param = { param: cryptography(model) };

        return postDataNotTimeOut("RelatoriosAnaliticos/ExecutarRelatorio", param, true);
    };

    self.excluirExecucao = function (id) {
        var model = { Value: id };
        var param = { param: cryptography(model) };

        return postData("RelatoriosAnaliticos/ExcluirExecucao", param, true);
    };

    self.downloadFile = function (id) {
        var model = { Value: id };
        var url = basePath.concat("RelatoriosAnaliticos/DownloadArquivo?param=", cryptography(model));
        window.open(url, "_blank");
    };
}
function MatMedPrecadRepository() {
    var self = this;

    self.salvarFabricante = function (model) {

        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "MaterialMedicamento/AdicionarFabricante",
            data: JSON.stringify({ 'param': cryptography(model) }),
            cache: false
        });
    };

    self.salvarMaterialMedicamento = function (model) {

        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath + "MaterialMedicamento/AdicionarMaterialMedicamento",
            data: JSON.stringify({ 'param': cryptography(model) }),
            cache: false
        });
    };

    self.prestadorPossuiMatMedGenerico = function (model) {
        return get("MaterialMedicamento/PrestadorPossuiMatMedGenerico", cryptography(model));
    };
    self.verificarMaterialExistente = function (model) {
        return get("MaterialMedicamento/VerificarMaterialExistente", cryptography(model));
    };
}

function LoteXmlRepository() {
    var self = this;

    this.base64ToArrayBuffer = function (base64) {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (var i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    };

    this.listarXmlsEnviados = function (model) {
        return get("RecebeXMLTISS/ListarXmlsEnviados", cryptography(model))
    }

    this.visualizarArquivoEnviado = function (id) {
        var model = { Value: id };
        return get("RecebeXMLTISS/VisualizarArquivoEnviado", cryptography(model))
    }

    this.downloadArquivoEnviado = function (id) {
        var model = { Value: id };
        window.open(basePath + "RecebeXMLTISS/DownloadArquivoEnviado?param=" + cryptography(model));
    }

    this.downloadCsvContratadosExecutantesValores = function (id) {
        var model = { Value: id };
        window.open(basePath + "RecebeXMLTISS/DownloadCsvContratadoExecutanteValores?param=" + cryptography(model));
    }
    

    this.printProtocolo = function (id) {
        var model = { Value: id };
        return get("RecebeXMLTISS/DownloadHtmlProtocolo", cryptography(model))
    }

    this.downloadProtocoloRecebidoXml = function (id) {
        var model = { Value: id };
        window.open('/RecebeXMLTISS/DownloadProtocoloRecebidoXml?param=' + cryptography(model), '_blank', '');
    }

    this.getAnexos = function (id) {
        var model = { Value: id };
        return get("RecebeXMLTISS/GetAnexosProtocolo", cryptography(model))
    }

    this.deleteFile = function (idDocumento, numeroProtocolo) {
        var model =
        {
            IdDocumento: idDocumento,
            NumeroProtocolo: numeroProtocolo
        };
        var param = { param: cryptography(model) };
        return postData("RecebeXMLTISS/DeleteDocumentoLote", param)
    }

    this.downloadFile = function (idDocumento, numeroProtocolo) {
        var model =
        {
            IdDocumento: idDocumento,
            NumeroProtocolo: numeroProtocolo
        };
        window.open('/RecebeXMLTISS/DownloadFile?param=' + cryptography(model), '_blank', '');
    }

    this.saveFile = function (numeroProtocolo, fileName, pathFileName) {
        var model =
        {
            NumeroProtocolo: numeroProtocolo,
            PathFileName: pathFileName,
            FileName: fileName
        };
        var param = { param: cryptography(model) };
        return postData("RecebeXMLTISS/SaveFile", param)
    }

    this.consultarSituacaoProtocolo = function (numeroProtocolo) {
        var model = { Value: numeroProtocolo };
        return get("/RecebeXMLTISS/CalcularSituacaoProtocolo?param=" + cryptography(model));
    }

    this.removerEnvioProtocolo = function (numeroProtocolo) {
        model = { Value: numeroProtocolo };
        return $.ajax({
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("/RecebeXMLTISS/RemoverEnvioProtocolo"),
            data: JSON.stringify(model),
            async: true,
            error: function (xhr, status, error) {
                alert(xhr.responseText);
            }
        });
    }

    this.cancelarPrevia = function (id) {
        var param = { param: cryptography({ Value: id }) };
        return postData("RecebeXMLTISS/CancelarPrevia", param, true);
    }

    this.efetivarPrevia = function (id, filePathTemp, fileName) {
        var param = { param: cryptography({ IdDocumento: id, PathFileName: filePathTemp, FileName: fileName }) };
        return postData("RecebeXMLTISS/EfetivarPrevia", param, true);
    }


    this.buscarParametroExigirAnexoAoEnviarXml = function (codigoPrestador) {
        var model = { Value: codigoPrestador };
        return get("/RecebeXMLTISS/BuscarParametroExigirAnexoAoEnviarXml?param=" + cryptography(model));
    }

    this.impressaoLoteXMLSintetico = function (numeroProtocolo) {
        return $.ajax({
            type: "POST",
            url: basePath + "RecebeXMLTISS/ImpressaoLoteXMLSintetico",
            data: { numeroProtocolo: numeroProtocolo },
            cache: false,
        })
    };
}

function EnvioRelatorioEmailAgendamentoRepository() {
    var self = this;

    self.get = function (model, success) {
        return $.ajax({
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            url: basePath.concat("/EnvioRelatorioEmailAgendamento/Get?param=", cryptography(model)),
            data: { param: model },
            success: success,
            cache: false,
            async: false
        });
    };
    self.getRelatorios = function () {
        return get("/EnvioRelatorioEmailAgendamento/GetRelatorios", null, false);
    };
    self.getNotificacoesByRelatorio = function (id) {
        return get("/EnvioRelatorioEmailAgendamento/GetNotificacoesByRelatorio/" + id, null, false);
    };

    self.save = function (model, success) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("/EnvioRelatorioEmailAgendamento/Save"),
            success: success,
            data: model,
            cache: false,
            async: false
        });
    };
    self.delete = function (model, success) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("/EnvioRelatorioEmailAgendamento/Delete"),
            success: success,
            data: model,
            cache: false,
            async: false
        });
    };
}

function ConversaoRepository() {
    var self = this;

    self.getArquivosByTipo = function (param) {
        return get("/Conversao/GetArquivosByTipo", cryptography(param));
    };
    self.getArquivos = function (param) {
        return get("/Conversao/GetArquivos", cryptography(param));
    };
    self.getLinhasResumidasConversao = function (param) {
        return get("/Conversao/GetLinhasResumidasConversao", cryptography(param));
    };

    self.getLinhasAgrupadasErro = function (param) {
        return get("/Conversao/GetInconsistenciasByArquivoAgrupadas", cryptography(param));
    };

    self.getLinhas = function (tipo, param) {
        switch (tipo) {

            case conversao.PesquisaAgrupadaComErro:
                return self.getLinhasAgrupadasErro(param);
            default:
                return self.getLinhasResumidasConversao(param);
        }
    }

    self.getInconsistencias = function (param) {
        return get("/Conversao/GetInconsistencias", cryptography(param));
    };

    self.getLinha = function (param) {
        return get("/Conversao/GetLinha", cryptography(param));
    };

    self.downloadFile = function (id) {
        var model = { ArquivoId: id };
        var url = basePath.concat("Conversao/DownloadArquivo?param=", cryptography(model));
        window.open(url, "_blank");
    };
}
function SimulacaoMensalidadeRepository() {
    var self = this;

    self.simular = function (filtro) {
        return $.ajax({
            type: "GET",
            url: basePath + "SimulacaoMensalidade/Simular",
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
}
function RadioAcidentadoRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarRadioAcidentado?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarRadioAcidentado", cryptography(model));
    }
}

function GastosUsuariosPASRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarCobrancaGastosUsuariosPAS?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarCobrancaGastosUsuariosPAS", cryptography(model));
    }
}

function UsuariosEC16Repository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarCobrancaUsuariosEC16?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarCobrancaUsuariosEC16", cryptography(model));
    }
}

function ContribuicaoUsuariosRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarCobrancaContribuicaoUsuarios?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarCobrancaContribuicaoUsuarios", cryptography(model));
    }

    self.pesquisar = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath.concat("RelatoriosIpasgoWebApi/PesquisarCobrancaContribuicaoUsuarios?param=", param),
            contentType: "application/json",
            dataType: "json",
            cache: false
        });
    };
}

function ControleFolhaConveniadasRepository() {
    var self = this;

    self.pesquisar = function (filtro, url) {
        return $.ajax({
            type: "GET",
            url: basePath + url,
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.upload = function (file, periodo, leiaute) {
        var pacote = new FormData();
        pacote.append(file.name, file);
        pacote.append("PERIODO", periodo);
        pacote.append("CODIGO_LEIAUTE", leiaute);

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/Upload",
            data: pacote,
            contentType: false,
            processData: false,
            cache: false
        });
    }

    self.excluirArquivo = function (idArquivo) {
        var model = JSON.stringify({ CodigoArquivo: idArquivo, SituacaoArquivo: -1 });

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/AlterarSituacaoImportacao",
            data: model,
            cache: false,
            dataType: "json",
            contentType: "application/json",
        });
    }

    self.efetivarArquivo = function (idArquivo) {
        var model = JSON.stringify({ CodigoArquivo: idArquivo, SituacaoArquivo: 3 });

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/AlterarSituacaoImportacao",
            data: model,
            cache: false,
            dataType: "json",
            contentType: "application/json",
        });
    }
}

function RelatoriosIpasgoWebApiRepository() {
    var self = this;

    self.gerarPdfDetalheParcelamento = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("RelatoriosIpasgoWebApi/GerarPdfDetalheParcelamento"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.name;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.error("Erro", xhr.responseText);
            }
        });
    };

}
function FinanceiroIpasgoWebApiRepository() {
    var self = this;

    self.validarCarteirinha = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath.concat("FinanceiroIpasgoWebApi/ValidarCarteirinha"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.solicitarParcelamento = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/SolicitarParcelamento"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.verParcelamentos = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/VerParcelamentos"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.verParcelamentosDet = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/VerParcelamentosDetalhes"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.simularParcelamento = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/SimularParcelamento"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.verDetalhesDivida = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/VerDetalhesDivida"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.concluirParcelamento = function (param) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("FinanceiroIpasgoWebApi/ConcluirParcelamento"),
            data: JSON.stringify(param),
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.obterFaixasParcelamento = function () {
        return $.ajax({
            type: "GET",
            url: basePath + "FinanceiroIpasgoWebApi/ObterFaixasParcelamento",
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };
}

function DemonstrativoCobrancaRepository() {
    var self = this;

    self.consultar = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath + "DemonstrativoCobranca/GetCobrancas",
            data: param,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.gerarPdfCompleto = function (param) {
        return $.ajax({
            type: "GET",
            url: basePath + "DemonstrativoCobranca/GerarDemonstrativo",
            data: param,
            contentType: "application/json",
            dataType: "json"
        });
    };
}

function RelacaoCobrancaDevolucaoRepository() {
    var self = this;

    self.gerarPdf = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("RelacaoCobrancaDevolucao/GerarCobrancaDevolucao"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };

    self.gerarCsv = function (param) {
        facil.exibirLoading(true);
        return $.ajax({
            type: "POST",
            dataType: "json",
            async: true,
            contentType: "application/json",
            url: basePath.concat("RelacaoCobrancaDevolucao/GerarCobrancaDevolucao"),
            data: JSON.stringify(param),
            cache: false,
            success: function (data) {
                facil.exibirLoading(false);
                const blob = new Blob([base64ToArrayBuffer(data.file)], { type: data.type });
                const file = new File([blob], data.name, { type: data.type });
                const url = URL.createObjectURL(file);
                window.open(url);
            },
            error: function (xhr, status, error) {
                facil.exibirLoading(false);
                facil.noty.warning('Atenção!', xhr.responseText, true);
            }
        });
    };
}

function RadioAcidentadoRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarRadioAcidentados?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarRadioAcidentados", cryptography(model));
    }
}

function GastosUsuariosPASRepository() {
    var self = this;

    self.gerar = function (param) {
        var url = basePath.concat("RelatoriosIpasgoWebApi/GerarCobrancaGastosUsuariosPAS?param=", cryptography(param));
        window.open(url, "_blank");
    };

    self.enviarEmail = function (model) {
        return get("RelatoriosIpasgoWebApi/GerarCobrancaGastosUsuariosPAS", cryptography(model));
    }
}

function ControleFolhaConveniadasRepository() {
    var self = this;

    self.pesquisar = function (filtro, url) {
        return $.ajax({
            type: "GET",
            url: basePath + url,
            data: filtro,
            cache: false,
            dataType: "json",
            contentType: "application/json"
        });
    };

    self.upload = function (file, periodo, leiaute) {
        var pacote = new FormData();
        pacote.append(file.name, file);
        pacote.append("PERIODO", periodo);
        pacote.append("CODIGO_LEIAUTE", leiaute);

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/Upload",
            data: pacote,
            contentType: false,
            processData: false,
            cache: false
        });
    }

    self.excluirArquivo = function (idArquivo) {
        var model = JSON.stringify({ CodigoArquivo: idArquivo, SituacaoArquivo: -1 });

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/AlterarSituacaoImportacao",
            data: model,
            cache: false,
            dataType: "json",
            contentType: "application/json",
        });
    }

    self.efetivarArquivo = function (idArquivo) {
        var model = JSON.stringify({ CodigoArquivo: idArquivo, SituacaoArquivo: 3 });

        return $.ajax({
            type: "POST",
            url: basePath + "ControleFolhaConveniadas/AlterarSituacaoImportacao",
            data: model,
            cache: false,
            dataType: "json",
            contentType: "application/json",
        });
    }
}

var cryptography = function () {

    /* Base64 string to array encoding */
    function uint6ToB64(nUint6) {
        return nUint6 < 26
            ? nUint6 + 65
            : nUint6 < 52
                ? nUint6 + 71
                : nUint6 < 62
                    ? nUint6 - 4
                    : nUint6 === 62
                        ? 43
                        : nUint6 === 63
                            ? 47
                            : 65;
    }

    function base64EncArr(aBytes) {
        let nMod3 = 2;
        let sB64Enc = "";

        const nLen = aBytes.length;
        let nUint24 = 0;
        for (let nIdx = 0; nIdx < nLen; nIdx++) {
            nMod3 = nIdx % 3;
            // To break your base64 into several 80-character lines, add:
            //   if (nIdx > 0 && ((nIdx * 4) / 3) % 76 === 0) {
            //      sB64Enc += "\r\n";
            //    }

            nUint24 |= aBytes[nIdx] << ((16 >>> nMod3) & 24);
            if (nMod3 === 2 || aBytes.length - nIdx === 1) {
                sB64Enc += String.fromCodePoint(
                    uint6ToB64((nUint24 >>> 18) & 63),
                    uint6ToB64((nUint24 >>> 12) & 63),
                    uint6ToB64((nUint24 >>> 6) & 63),
                    uint6ToB64(nUint24 & 63)
                );
                nUint24 = 0;
            }
        }
        return (
            sB64Enc.substring(0, sB64Enc.length - 2 + nMod3) +
            (nMod3 === 2 ? "" : nMod3 === 1 ? "=" : "==")
        );
    }

    function strToUTF8Arr(sDOMStr) {
        let aBytes;
        let nChr;
        const nStrLen = sDOMStr.length;
        let nArrLen = 0;

        /* mapping… */
        for (let nMapIdx = 0; nMapIdx < nStrLen; nMapIdx++) {
            nChr = sDOMStr.codePointAt(nMapIdx);

            if (nChr >= 0x10000) {
                nMapIdx++;
            }

            nArrLen +=
                nChr < 0x80
                    ? 1
                    : nChr < 0x800
                        ? 2
                        : nChr < 0x10000
                            ? 3
                            : nChr < 0x200000
                                ? 4
                                : nChr < 0x4000000
                                    ? 5
                                    : 6;
        }

        aBytes = new Uint8Array(nArrLen);

        /* transcription… */
        let nIdx = 0;
        let nChrIdx = 0;
        while (nIdx < nArrLen) {
            nChr = sDOMStr.codePointAt(nChrIdx);
            if (nChr < 128) {
                /* one byte */
                aBytes[nIdx++] = nChr;
            } else if (nChr < 0x800) {
                /* two bytes */
                aBytes[nIdx++] = 192 + (nChr >>> 6);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else if (nChr < 0x10000) {
                /* three bytes */
                aBytes[nIdx++] = 224 + (nChr >>> 12);
                aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else if (nChr < 0x200000) {
                /* four bytes */
                aBytes[nIdx++] = 240 + (nChr >>> 18);
                aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
                nChrIdx++;
            } else if (nChr < 0x4000000) {
                /* five bytes */
                aBytes[nIdx++] = 248 + (nChr >>> 24);
                aBytes[nIdx++] = 128 + ((nChr >>> 18) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
                nChrIdx++;
            } /* if (nChr <= 0x7fffffff) */ else {
                /* six bytes */
                aBytes[nIdx++] = 252 + (nChr >>> 30);
                aBytes[nIdx++] = 128 + ((nChr >>> 24) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 18) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 12) & 63);
                aBytes[nIdx++] = 128 + ((nChr >>> 6) & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
                nChrIdx++;
            }
            nChrIdx++;
        }

        return aBytes;
    }

    return function (param) {

        const aMyUTF8Input = strToUTF8Arr(JSON.stringify(param));
        const sMyBase64 = base64EncArr(aMyUTF8Input);

        return sMyBase64;
    }
}();

function AccountRepository() {
    var self = this;

    self.GetBeneficiariosGrupo = function () {
        return $.ajax({
            type: "POST",
            url: basePath.concat("Account/GetBeneficiariosGrupo"),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    };

    self.ChangeAccount = function (codSeg) {
        return $.ajax({
            type: "POST",
            url: basePath.concat("Account/ChangeAccount"),
            data: JSON.stringify({ Value: codSeg }),
            dataType: "json",
            contentType: "application/json",
            cache: false
        });
    };
};
