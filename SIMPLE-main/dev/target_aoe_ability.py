def get_flattened_4x4_matrix(matrix, row, col):
    flatten_matrix = []
    for i in range(row - 1, row + 3):
        for j in range(col - 1, col + 3):
            if 0 <= i < 20 and 0 <= j < 20:
                flatten_matrix.append(matrix[i][j])
    return flatten_matrix

x = []
counter = 0
for i in range(20):
    y = []
    for j in range(20):
        y.append(counter)
        counter += 1
    x.append(y)

#print(x[10][10])
values = get_flattened_4x4_matrix(x, 0, 0)
print(values)