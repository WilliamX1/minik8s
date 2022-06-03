#include <cuda_runtime.h>
#include <iostream>
#include <vector>
#include <fstream>

using namespace std;

__global__ void add_gpu(int *d_matrixA, int *d_matrixB, int *d_matrixC, int x, int y) {
    int ix = threadIdx.x + blockDim.x*blockIdx.x;
	int iy = threadIdx.y + blockDim.y*blockIdx.y;
	unsigned int idx = iy * x + ix;
	if (ix < x && iy < y){
		d_matrixC[idx] = d_matrixA[idx] + d_matrixB[idx];
	}
}




vector<vector<int>> matrix_add(vector<vector<int>> &a, vector<vector<int>> &b) {
    const int m = a.size(), n = a[0].size();
    int *matrixA = (int *)malloc(sizeof(int) * m * n);
    int *matrixB = (int *)malloc(sizeof(int) * m * n);
    int *matrixC = (int *)malloc(sizeof(int) * m * n);
    // cout << "矩阵输入:" << endl;
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            matrixA[i * n + j] = a[i][j];
            matrixB[i * n + j] = b[i][j];
        }
        // for (int j = 0; j < n; j++) {
        //     cout << matrixA[i * n + j] << " ";
        // }
        // cout << "    ";
        // for (int j = 0; j < n; j++) {
        //     cout << matrixB[i * n + j] << " ";
        // }
        // cout << endl;
    }

    int *d_matrixA, *d_matrixB, *d_matrixC;
    cudaMalloc((void **)&d_matrixA, sizeof(int) * n * m);
    cudaMalloc((void **)&d_matrixB, sizeof(int) * n * m);
    cudaMalloc((void **)&d_matrixC, sizeof(int) * n * m);
    cudaMemcpy(d_matrixA, matrixA, sizeof(int) * n * m, cudaMemcpyHostToDevice);
    cudaMemcpy(d_matrixB, matrixB, sizeof(int) * n * m, cudaMemcpyHostToDevice);
    int x = n,y = m;
    int dimx = 32;
    int dimy = 32;
	dim3 block(dimx, dimy);
    dim3 grid(x / block.x + 1, y / block.y + 1);
    add_gpu<<<grid, block>>>(d_matrixA, d_matrixB, d_matrixC, x, y);
    cudaMemcpy(matrixC, d_matrixC, sizeof(int) * n * m, cudaMemcpyDeviceToHost);
    vector<int> temp(n, 0);
    vector<vector<int>> c(m, temp);
    // cout << "结果输出:" << endl;
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            c[i][j] = matrixC[i * n + j];
            // cout << matrixC[i * n + j] << " ";
        }
        // cout << endl;
    }
    free(matrixA);
    free(matrixB);
    free(matrixC);
    cudaFree(d_matrixA);
    cudaFree(d_matrixB);
    cudaFree(d_matrixC);
    return c;
}

int main(int argc, char *argv[]) {
    vector<vector<int>> a{{1,2,3},{2,3,4},{3,4,5}}, b{{1,2,3},{4,5,6},{7,8,9}};
    vector<vector<int>> c = matrix_add(a, b);
    ofstream infile;
    infile.open("add.out");
    for (int i = 0; i < c.size(); i++){
        for (int j = 0; j < c[0].size(); j++){
            infile << c[i][j] << " ";
        }
        infile << "\n";
    }

    return 0;
}