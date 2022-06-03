#include <cuda_runtime.h>
#include <iostream>
#include <vector>
#include <fstream>
#include <time.h>

using namespace std;

void init_matrix(int *matrix, int size){
	for (int i = 0; i < size; i++){
		matrix[i] = (int)(rand() & 0xff) / 66.6;
	}
}

void add_cpu(int *matrixA, int *matrixB, int *matrixC, int x, int y){
	int *a = matrixA, *b = matrixB, *c = matrixC;
	for (int iy = 0; iy < y; iy++){
		for (int ix = 0; ix < x; ix++){
			c[ix] = a[ix] + b[ix];
		}
		a += x;
		b += x;
		c += x;
	}
}

__global__ void add_gpu(int *d_matrixA, int *d_matrixB, int *d_matrixC, int x, int y) {
    int ix = threadIdx.x + blockDim.x*blockIdx.x;
	int iy = threadIdx.y + blockDim.y*blockIdx.y;
	unsigned int idx = iy * x + ix;
	if (ix < x && iy < y){
		d_matrixC[idx] = d_matrixA[idx] + d_matrixB[idx];
	}
}

void print_result(int *matrixC, int *matrixCC, int x, int y){
	int *c = matrixC, *cc = matrixCC;
	for (int iy = 0; iy < y; iy++)
	{
		for (int ix = 0; ix < x; ix++)
		{
			printf("%d - %d = %d    ", c[ix], cc[ix],  c[ix]-cc[ix]);
		}
		c += x;
		cc += x;
		printf("\n");
	}
	printf("\n");
}


void matrix_add_compare() {
    int m = 1<<14;
	int n = 1<<14;
    int *matrixA = (int *)malloc(sizeof(int) * m * n);
    int *matrixB = (int *)malloc(sizeof(int) * m * n);
    int *matrixC = (int *)malloc(sizeof(int) * m * n);
    int *matrixCC = (int *)malloc(sizeof(int) * m * n);
    init_matrix(matrixA, m * n);
    init_matrix(matrixB, m * n);
    int x = n, y = m;
    clock_t cpuStart = clock();
    add_cpu(matrixA, matrixB, matrixCC, x, y);
    clock_t cpuEnd = clock();
    float cpuTime = (float)(cpuEnd - cpuStart) / CLOCKS_PER_SEC;
	printf("cpu time:%f\n", cpuTime);
    int *d_matrixA, *d_matrixB, *d_matrixC;
    cudaMalloc((void **)&d_matrixA, sizeof(int) * n * m);
    cudaMalloc((void **)&d_matrixB, sizeof(int) * n * m);
    cudaMalloc((void **)&d_matrixC, sizeof(int) * n * m);
    cudaMemcpy(d_matrixA, matrixA, sizeof(int) * n * m, cudaMemcpyHostToDevice);
    cudaMemcpy(d_matrixB, matrixB, sizeof(int) * n * m, cudaMemcpyHostToDevice);

    int dimx = 32;
    int dimy = 32;
	dim3 block(dimx, dimy);
    dim3 grid(x / block.x + 1, y / block.y + 1);
    clock_t gpuStart = clock();
    add_gpu<<<grid, block>>>(d_matrixA, d_matrixB, d_matrixC, x, y);
    clock_t gpuEnd = clock();
    float gpuTime = (float)(gpuEnd - gpuStart) / CLOCKS_PER_SEC;
	printf("gpu time:%f\n", gpuTime);
    cudaMemcpy(matrixC, d_matrixC, sizeof(int) * n * m, cudaMemcpyDeviceToHost);
    // cout << "检验结果:" << endl;
    // print_result(matrixC, matrixCC, x, y);
    free(matrixA);
    free(matrixB);
    free(matrixC);
    free(matrixCC);
    cudaFree(d_matrixA);
    cudaFree(d_matrixB);
    cudaFree(d_matrixC);
}

int main(int argc, char *argv[]) {
    matrix_add_compare();
    return 0;
}