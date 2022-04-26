import graphviz as gz

dot = gz.Digraph(comment='The Round Table')
dot.node('A', 'King Arthur')
dot.node('B', 'Sir Bedevere the Wise')
dot.node('L', 'Sir Lancelot the Brave')

dot.edges(['AB', 'AL'])
dot.edge('B', 'L', constraint='false')
dot.edges(['BB'])

print(dot.source)

dot.render('output/round-table').replace('\\', '/')