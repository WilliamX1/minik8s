#include <iostream>
#include <vector>
#include <cuda_runtime.h>

using namespace std;

void init_matrix(int *matrix, int size){
	for (int i = 0; i < size; i++){
		matrix[i] = (int)(rand() & 0xff) / 66.6;
	}
}

void multi_cpu(int *d_matrixA, int *d_matrixB, int *d_matrixC, int m, int n, int o){
    for (int iy = 0; iy < m; iy++){
        for (int ix = 0; ix < o; ix++){
            int c = 0;
            for (int k = 0; k < n; k++){
                c += d_matrixA[iy * n + k] * d_matrixB[k * o + ix];
            }
            d_matrixC[iy * o + ix] = c;
        }
    }
}

__global__ void multi_gpu(int *d_matrixA, int *d_matrixB, int *d_matrixC, int m, int n, int o){
    int ix = blockIdx.x * blockDim.x + threadIdx.x;
    int iy = blockIdx.y * blockDim.y + threadIdx.y;
    if(iy < m && ix < o) {
        int temp = 0;
        for(int i = 0; i < n; ++i){
            temp += d_matrixA[iy * n + i] * d_matrixB[i * o + ix];
        }
        d_matrixC[iy * o + ix] = temp;
        
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
}

void matrix_multi(){
    int m = 1<<6;
	int n = 1<<10;
    int o = 1<<8;
    int *matrixA = (int *)malloc(sizeof(int) * m * n);
    int *matrixB = (int *)malloc(sizeof(int) * n * o);
    int *matrixC = (int *)malloc(sizeof(int) * m * o);
    int *matrixCC = (int *)malloc(sizeof(int) * m * o);
    init_matrix(matrixA, m * n);
    init_matrix(matrixB, n * o);
    clock_t cpuStart = clock();
    multi_cpu(matrixA, matrixB, matrixCC, m, n, o);
    clock_t cpuEnd = clock();
    float cpuTime = (float)(cpuEnd - cpuStart) / CLOCKS_PER_SEC;
	printf("cpu time:%f\n", cpuTime);
    int *d_matrixA, *d_matrixB, *d_matrixC;
    cudaMalloc((void **)&d_matrixA, sizeof(int) * m * n);
    cudaMalloc((void **)&d_matrixB, sizeof(int) * n * o);
    cudaMalloc((void **)&d_matrixC, sizeof(int) * m * o);
    cudaMemcpy(d_matrixA, matrixA, sizeof(int) * m * n, cudaMemcpyHostToDevice);
	cudaMemcpy(d_matrixB, matrixB, sizeof(int) * n * o, cudaMemcpyHostToDevice);
    int dimx = 32;
    int dimy = 32;
	dim3 block(dimx, dimy);
    dim3 grid(o / block.x + 1, m / block.y + 1);
    clock_t gpuStart = clock();
    multi_gpu<<<grid, block>>>(d_matrixA, d_matrixB, d_matrixC, m, n, o);
    clock_t gpuEnd = clock();
    float gpuTime = (float)(gpuEnd - gpuStart) / CLOCKS_PER_SEC;
	printf("gpu time:%f\n", gpuTime);
    cudaMemcpy(matrixC, d_matrixC, sizeof(int) * m * o, cudaMemcpyDeviceToHost);
    cout << "检验结果:" << endl;
    print_result(matrixC, matrixCC, o, m);
    free(matrixA);
    free(matrixB);
    free(matrixC);
    free(matrixCC);
    cudaFree(d_matrixA);
    cudaFree(d_matrixB);
    cudaFree(d_matrixC);
}

int main(int argc, char *argv[])
{
    matrix_multi();
    return 0;
}