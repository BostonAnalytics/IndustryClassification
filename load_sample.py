from pyspark.sql import SparkSession
import sys

def main():
    try:
        # Initialize Spark Session
        spark = SparkSession.builder \
            .appName("LoadSample") \
            .master("local[*]") \
            .getOrCreate()

        print("Loading Parquet files from E:/Data/Jobs_2026_US/...")
        
        # Load a single parquet file to avoid globbing issues on Windows without winutils
        df = spark.read.parquet("E:/Data/Jobs_2026_US/jobs_2026_part_00001.parquet")
        
        print("\n--- Schema ---")
        df.printSchema()
        
        print("\n--- Sample Data (5 rows) ---")
        df.show(5, truncate=True)
        
        print(f"\nTotal Number of Records: {df.count()}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'spark' in locals():
            spark.stop()

if __name__ == "__main__":
    main()
