"""
    Data Visualization
"""

"""
    loadFiles
        Input: 
            num_of_nodes
            num_of_instances
            dataType
        Output:
            list of loaded files
        Description:
            Saves multiple txt files into lists
                delay_node1-1.txt -> delays[0]
                delay_node1-2.txt -> delays[1]
                ...
                delay_node10-2.txt -> delays[20]
"""
def loadFiles(num_of_nodes, num_of_instances, dataType):
    files = list()
    for i in range(1, num_of_nodes+1):
        for j in range(1, num_of_instances+1):
            F = open(str(dataType) + "_node" + str(i) +"-"+ str(j) +".txt","r")
            files.append(F) 

    print("Load Complete")
    return files

'''
    parseColumn
        Description:
            Serialize txt data into a list
            Data is saved as below
                0
                1       ---->   0 1 2 10
                2
                10
'''
def parseColumn(file, col):
    l = list()
    for line in file:
        l.append(line.split()[col])

    print("Parsing Complete")
    return l        

   