from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

graph_attr = {
    "fillcolor": "turquoise",
    "fontsize": "50",
    "pad": "2.0",
    "ranksep": "2.0",      # more vertical space between ranks
    "nodesep": "1.5",      # more horizontal space between nodes
}

node_attr = {
    "fontsize": "28",      # bigger label text
    "labelloc": "b",       # force label to BOTTOM, outside the icon box
    "labeldistance": "2",
    "margin": "0.6,0.5",   # more internal padding
    "width": "2.8",        # wider node so label has room
    "height": "2.8",       # taller node so icon and label don't overlap
    "imagescale": "true",  # scale icon to fit within the node box
    "fixedsize": "true",   # honour width/height strictly
}

with Diagram(
    "sam-test-app",
    show=False,
    filename="./architecture_diagram",
    outformat=["png", "pdf", "jpg"],
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="TB",
):
    lb = ELB("lb")
    db = RDS("events")

    lb >> EC2("worker1") >> db
    lb >> EC2("worker2") >> db
    lb >> EC2("worker3") >> db
    lb >> EC2("worker4") >> db
    lb >> EC2("worker5") >> db