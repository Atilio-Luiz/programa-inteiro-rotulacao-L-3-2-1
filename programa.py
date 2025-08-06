####################################################
##
## Integer Program for L(3,2,1)-labeling
## Author: Atilio Gomes Luiz
## Date: 5th August, 2024
##
####################################################
from ortools.linear_solver import pywraplp
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path
import time
import csv

# Caminhos de entrada e saída
input_directory_name = "cycles"
pasta_entrada = Path(input_directory_name)
pasta_saida = Path("results_"+input_directory_name)
pasta_saida.mkdir(exist_ok=True)
pasta_saida_rotulacao = Path("labelings_"+input_directory_name)
pasta_saida_rotulacao.mkdir(exist_ok=True)

TIME_LIMIT_MINUTES = 15   # tempo máximo que o solver tem para cada instância

# Esta função computa os vizinhos de cada vértice 
# e devolve em formato de dicionário
def _neighbors_at_distance_1(graph):
    return {u: set(graph.neighbors(u)) for u in graph.nodes()}

# Esta função computa os vizinhos à distância 2 de cada 
# vértice e devolve em formato de dicionário
def _neighbors_at_distance_2(graph, dist1):
    dist2 = dict()
    for v in graph:
        dist2[v] = set()
        for u in graph[v]:
            for w in graph[u]:
                if w != v and w not in dist1[v]:
                    dist2[v].add(w)
    return dist2

# Esta função computa os vizinhos à distância 3 de cada 
# vértice e devolve em formato de dicionário
def _neighbors_at_distance_3(graph, dist1, dist2):
    dist3 = dict()
    for v in graph:
        dist3[v] = set()
        for u in graph[v]:
            for w in graph[u]:
                for z in graph[w]:
                    if z != u and z != v and z not in dist2[v] and z not in dist1[v]:
                        dist3[v].add(z)
    return dist3

# Função que salva uma imagem do grafo em arquivo png
def draw_graph(G, graph_name):
    # Computa as posições dos nós
    pos = nx.spring_layout(G)

    # Desenha o grafo
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=200, font_size=10)

    # Salva figura em aquivo
    plt.savefig(graph_name+".png")
    plt.clf() 

# Função que lê o grafo do arquivo e executa o solver 
def processar_arquivo(arquivo_path):
    G = nx.read_edgelist(arquivo_path, nodetype=int)
    G.remove_edges_from([(u, v) for u, v in G.edges() if u == v])

    draw_graph(G, arquivo_path.stem)

    edge_count = len(G.edges())
    vertex_count = len(G.nodes())
    density = (2.0 * edge_count) / (vertex_count * (vertex_count - 1)) if vertex_count > 1 else 0.0
    max_degree = max(dict(G.degree()).values(), default=0)
    min_degree = min(dict(G.degree()).values(), default=0)

    dist1 = _neighbors_at_distance_1(G)
    dist2 = _neighbors_at_distance_2(G, dist1)
    dist3 = _neighbors_at_distance_3(G, dist1, dist2)

    msolver = pywraplp.Solver('L(3,2,1)-labeling', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
    if not msolver:
        raise Exception("CBC solver not available.")

    # Variáveis do modelo
    x = [msolver.IntVar(0, msolver.infinity(), f'x_{i}') for i in range(len(G))]
    z = msolver.IntVar(0, msolver.infinity(), 'z')
    
    # Restrição
    for i in range(len(G)):
        msolver.Add(x[i] <= z)

    # Função auxiliar para definição das restrições de distância
    def add_constraints(dist_dict, k, b):
        M = max_degree**3 + 2 * max_degree + 3
        for i in range(len(G)):
            for j in dist_dict[i]:
                if i < j:
                    b[(i, j)] = msolver.IntVar(0, 1, f'b_{i}_{j}')
                    msolver.Add(x[i] - x[j] >= k - M * (1 - b[(i, j)]))
                    msolver.Add(x[j] - x[i] >= k - M * b[(i, j)])

    # Restrições de distâncias
    b = {}
    add_constraints(dist1, 3, b)
    add_constraints(dist2, 2, b)
    add_constraints(dist3, 1, b)

    # Função objetivo
    msolver.Minimize(z)

    msolver.SetTimeLimit(TIME_LIMIT_MINUTES * 60 * 1000) # tempo em milisegundos

    mstatus = msolver.Solve()

    if mstatus == pywraplp.Solver.OPTIMAL:
        nome_csv = pasta_saida_rotulacao / f"{arquivo.stem}.csv"
        with open(nome_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["vertex", "label"])
            for i in list(G.nodes()):
                writer.writerow([i, x[i].solution_value()])
        return (vertex_count, edge_count, density, max_degree, min_degree, msolver.wall_time(), msolver.Objective().Value(), "OPTIMAL")
    elif mstatus == pywraplp.Solver.FEASIBLE:
        nome_csv = pasta_saida_rotulacao / f"{arquivo.stem}.csv"
        with open(nome_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["vertex", "label"])
            for i in list(G.nodes()):
                writer.writerow([i, x[i].solution_value()])
        return (vertex_count, edge_count, density, max_degree, min_degree, msolver.wall_time(), msolver.Objective().Value(), "BEST FOUND")
    else:
        return (vertex_count, edge_count, density, max_degree, min_degree, msolver.wall_time(), -1, "INFEASIBLE")
    

    
# Iterar pelos arquivos txt na pasta de entrada
for arquivo in pasta_entrada.glob("*.txt"):
    try:
        resultado = processar_arquivo(arquivo)
        nome_csv = pasta_saida / f"{arquivo.stem}.csv"
        with open(nome_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["graph", "#vertices", "#edges", "density", "max_degree", "min_degree", "time(ms)", "lambda", "status"])
            writer.writerow([
                arquivo.stem,
                resultado[0],
                resultado[1],
                f"{resultado[2]:.5f}",
                resultado[3],
                resultado[4],
                f"{resultado[5]:.2f}",
                resultado[6],
                resultado[7]                
            ])
        print(f"[OK] {arquivo.name} → {nome_csv.name}")
    except Exception as e:
        print(f"[XX] Erro ao processar {arquivo.name}: {e}")
